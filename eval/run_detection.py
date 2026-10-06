"""Grammar-point detection precision and recall over the labeled passages.

Scored per passage as sets of catalog ids: the question is "was this grammar
point found in this text", not how many times it occurs.

は and が appear in almost every Japanese sentence and are trivially matched,
so they would inflate a single headline number. The report gives the figure
with and without them.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kotoba.grammar_detect import detect, load_catalog  # noqa: E402
from kotoba.tokenizer import tokenize  # noqa: E402

TRIVIAL = {"g-wa-001", "g-ga-001"}


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}


def main() -> int:
    passages = [json.loads(l) for l in (ROOT / "eval" / "passages.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    pattern_of = {e.id: e.pattern for e in load_catalog()}

    rows, per_pattern = [], defaultdict(lambda: [0, 0, 0])
    totals = [0, 0, 0]
    nontrivial = [0, 0, 0]

    for p in passages:
        got = {d.catalog_id for d in detect(tokenize(p["text"]))}
        want = set(p["labels"])
        tp, fp, fn = want & got, got - want, want - got
        rows.append({
            "id": p["id"], "text": p["text"],
            "tp": sorted(tp), "fp": sorted(fp), "fn": sorted(fn), "note": p["note"],
        })
        for name, s in (("tp", tp), ("fp", fp), ("fn", fn)):
            i = ["tp", "fp", "fn"].index(name)
            totals[i] += len(s)
            nontrivial[i] += len(s - TRIVIAL)
            for cid in s:
                per_pattern[cid][i] += 1

    overall, strict = prf(*totals), prf(*nontrivial)
    print(f"{len(passages)} passages, {sum(len(p['labels']) for p in passages)} labels\n")
    print(f"  all points          precision {overall['precision']:.3f}  recall {overall['recall']:.3f}  f1 {overall['f1']:.3f}")
    print(f"  excluding は / が   precision {strict['precision']:.3f}  recall {strict['recall']:.3f}  f1 {strict['f1']:.3f}")

    print("\n  per pattern (tp/fp/fn):")
    for cid, (tp, fp, fn) in sorted(per_pattern.items(), key=lambda kv: -sum(kv[1])):
        print(f"    {pattern_of.get(cid, cid):<16} {tp:>3} / {fp:>3} / {fn:>3}")

    bad = [r for r in rows if r["fp"] or r["fn"]]
    print(f"\n  passages with an error: {len(bad)}")
    for r in bad:
        marks = []
        if r["fp"]:
            marks.append("FP " + ",".join(pattern_of.get(c, c) for c in r["fp"]))
        if r["fn"]:
            marks.append("FN " + ",".join(pattern_of.get(c, c) for c in r["fn"]))
        print(f"    {r['id']} {r['text'][:34]:<36} {'; '.join(marks)}")
        if r["note"]:
            print(f"           note: {r['note']}")

    out = ROOT / "eval" / "results" / "detection.json"
    out.write_text(json.dumps(
        {"overall": overall, "excluding_wa_ga": strict,
         "per_pattern": {pattern_of.get(k, k): dict(zip(("tp", "fp", "fn"), v)) for k, v in per_pattern.items()},
         "per_passage": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
