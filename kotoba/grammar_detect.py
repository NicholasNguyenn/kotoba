"""Match tokens to catalog patterns, and verify LLM-proposed candidates.

The rule that makes Kotoba's numbers meaningful: the LLM may *propose* grammar
points, but only points confirmed against a catalog entry survive.

Patterns are written as lemma sequences, not surface strings, because the
tokenizer already normalizes conjugation: 食べなかった yields ない, and のに
yields two particle tokens rather than one.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from kotoba.tokenizer import Token

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "grammar_catalog.jsonl"


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    pattern: str
    level: str
    meaning: str
    explanation: str
    match: tuple[tuple[str, str | None], ...]
    source: str
    verified: bool


@dataclass(frozen=True)
class DetectedPoint:
    catalog_id: str
    pattern: str
    span: tuple[int, int]
    confirmed: bool


@lru_cache(maxsize=4)
def load_catalog(path: Path | None = None) -> tuple[CatalogEntry, ...]:
    path = path or CATALOG_PATH
    entries = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            entries.append(
                CatalogEntry(
                    id=r["id"],
                    pattern=r["pattern"],
                    level=r["level"],
                    meaning=r["meaning"],
                    explanation=r["explanation"],
                    match=tuple((m[0], m[1] if len(m) > 1 else None) for m in r["match"]),
                    source=r["source"],
                    verified=r.get("verified", False),
                )
            )
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            # The catalog is the evidence; a silently skipped entry would show
            # up later as an unexplained drop in detection recall.
            raise ValueError(f"{path}:{n} is not a valid catalog entry: {exc}") from exc
    return tuple(entries)


def unverified(catalog: tuple[CatalogEntry, ...] | None = None) -> list[str]:
    """Entry ids not yet checked against a textbook or a teacher."""
    return [e.id for e in (catalog or load_catalog()) if not e.verified]


def _matches_at(entry: CatalogEntry, tokens: list[Token], i: int) -> bool:
    if i + len(entry.match) > len(tokens):
        return False
    for (lemma, pos), tok in zip(entry.match, tokens[i:]):
        if tok.lemma != lemma or (pos and tok.pos != pos):
            return False
    return True


def detect(
    tokens: list[Token], catalog: tuple[CatalogEntry, ...] | None = None
) -> list[DetectedPoint]:
    catalog = catalog or load_catalog()
    # ponytail: overlapping matches are all reported, longest first. Add
    # overlap resolution only if Phase 4 precision shows double-counting.
    found = [
        DetectedPoint(e.id, e.pattern, (i, i + len(e.match)), True)
        for i in range(len(tokens))
        for e in catalog
        if _matches_at(e, tokens, i)
    ]
    return sorted(found, key=lambda d: (d.span[0], d.span[0] - d.span[1]))


def confirm_candidates(
    candidates: list[str],
    tokens: list[Token],
    catalog: tuple[CatalogEntry, ...] | None = None,
) -> list[DetectedPoint]:
    """Check LLM-proposed patterns against what the catalog actually matched.

    Rejects are returned with confirmed=False rather than dropped, so Phase 4
    can count what the model proposed and the catalog refused.
    """
    found = {d.pattern: d for d in detect(tokens, catalog)}
    return [found.get(c, DetectedPoint("", c, (-1, -1), False)) for c in candidates]
