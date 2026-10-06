"""Retrieval modes compared in Phase 3, plus the JLPT rerank from Phase 6.

All four modes go through one function so the eval harness can sweep them
without touching anything else, and so they provably share the same index,
the same embedding and the same top-k.

  keyword          BM25 over the ja.microsoft / en.microsoft text fields
  vector           pure ANN over the embedding field
  hybrid           both, fused by Reciprocal Rank Fusion (Azure does this)
  hybrid_semantic  hybrid, then Microsoft's semantic ranker reorders the top 50
"""

from enum import StrEnum
from typing import Any

from azure.search.documents.models import VectorizedQuery

from kotoba.azure_clients import embed
from kotoba.config import Settings, get_settings
from kotoba.search_index import search_client

SELECT = ["id", "doc_type", "pattern", "content_ja", "content_en", "jlpt_level", "source"]

# A learner at level N sees everything at or below it boosted. Index 0 is N5
# (easiest), so a lower index is more elementary.
JLPT_ORDER = ["N5", "N4", "N3", "N2", "N1"]


class Mode(StrEnum):
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"
    HYBRID_SEMANTIC = "hybrid_semantic"


def _jlpt_rerank(results: list[dict], level: str, boost: float = 0.5) -> list[dict]:
    """Promote documents at or below the learner's level. (Phase 6)

    Applied after retrieval rather than as a filter: a harder document that is
    the only correct answer should still be reachable, just ranked lower.
    """
    ceiling = JLPT_ORDER.index(level)

    def key(d: dict) -> float:
        lvl = d.get("jlpt_level")
        if lvl in JLPT_ORDER and JLPT_ORDER.index(lvl) <= ceiling:
            return -(d["_score"] + boost)
        return -d["_score"]

    return sorted(results, key=key)


def _search(
    query: str, mode: Mode, top: int, s: Settings, odata_filter: str | None = None
) -> list[dict[str, Any]]:
    client = search_client(settings=s)

    kwargs: dict[str, Any] = {"top": top, "select": SELECT}
    if odata_filter:
        kwargs["filter"] = odata_filter

    if mode is Mode.VECTOR:
        kwargs["search_text"] = None
    else:
        kwargs["search_text"] = query

    if mode in (Mode.VECTOR, Mode.HYBRID, Mode.HYBRID_SEMANTIC):
        kwargs["vector_queries"] = [
            VectorizedQuery(
                vector=embed([query], s)[0],
                # Over-fetch neighbours relative to `top`: RRF fuses two ranked
                # lists, so a document can place well overall without being in
                # either list's top 5.
                k_nearest_neighbors=max(top, 50),
                fields="embedding",
            )
        ]

    if mode is Mode.HYBRID_SEMANTIC:
        kwargs["query_type"] = "semantic"
        kwargs["semantic_configuration_name"] = s.semantic_config_name

    results = []
    for d in client.search(**kwargs):
        doc = {k: d.get(k) for k in SELECT}
        # The semantic ranker's score lives on a different field; prefer it
        # when present so the rerank is what actually orders the output.
        doc["_score"] = d.get("@search.reranker_score") or d.get("@search.score") or 0.0
        results.append(doc)
    return results


def retrieve(
    query: str,
    mode: Mode = Mode.HYBRID,
    top: int = 5,
    jlpt_level: str | None = None,
    prefer_type: str | None = None,
    reserve: int = 3,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Retrieve evidence.

    `prefer_type` reserves slots for one doc_type. A grammar question needs a
    grammar entry to answer from: the corpus holds 1,400 Tatoeba sentences
    against 14 catalog entries, so an unreserved top-5 is usually all example
    sentences, and an example sentence demonstrates a pattern without
    explaining it. Measured cost of not doing this is in the README.
    """
    s = settings or get_settings()

    results = _search(query, mode, top, s)
    if prefer_type:
        preferred = _search(
            query, mode, min(reserve, top), s, odata_filter=f"doc_type eq '{prefer_type}'"
        )
        seen = {d["id"] for d in preferred}
        results = preferred + [d for d in results if d["id"] not in seen]

    if jlpt_level:
        results = _jlpt_rerank(results, jlpt_level)
    return results[:top]
