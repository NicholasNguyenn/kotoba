"""Recall@5 and MRR for every retrieval mode, per language.

Questions with empty gold are abstention cases: they cannot contribute to
recall, so they are excluded from it and counted separately.

    python eval/run_retrieval.py            all four modes
    python eval/run_retrieval.py --top 10   different cutoff
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kotoba.retriever import Mode, retrieve  # noqa: E402

QUESTIONS = ROOT / "eval" / "questions.jsonl"
RESULTS = ROOT / "eval" / "results"


def load_questions() -> list[dict]:
    return [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]


def score_one(question: dict, hits: list[dict], top: int) -> dict:
    ids = [h["id"] for h in hits][:top]
    gold = set(question["gold"])
    # Recall@k here is "did any gold document land in the top k", which is the
    # question a learner actually cares about: was the right page found at all.
    found = bool(gold & set(ids))
    rr = 0.0
    for rank, doc_id in enumerate(ids, 1):
        if doc_id in gold:
            rr = 1 / rank
            break
    return {"id": question["id"], "hit": found, "rr": rr, "returned": ids}


def run_mode(mode: Mode, questions: list[dict], top: int) -> dict:
    scored, latencies = [], []
    for q in questions:
        t0 = time.perf_counter()
        hits = retrieve(q["query"], mode=mode, top=top)
        latencies.append((time.perf_counter() - t0) * 1000)
        scored.append({**score_one(q, hits, top), "lang": q["lang"], "kind": q["kind"]})
    latencies.sort()
    return {
        "mode": str(mode),
        "top": top,
        "per_question": scored,
        "p50_ms": round(latencies[len(latencies) // 2], 1),
    }


def summarize(run: dict, questions: list[dict]) -> dict:
    gold_qs = {q["id"] for q in questions if q["gold"]}
    rows = [s for s in run["per_question"] if s["id"] in gold_qs]
    out = {"all": _agg(rows)}
    for lang in ("en", "ja", "mixed"):
        out[lang] = _agg([r for r in rows if r["lang"] == lang])
    return out


def _agg(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0, "recall": None, "mrr": None}
    return {
        "n": len(rows),
        "recall": round(sum(r["hit"] for r in rows) / len(rows), 3),
        "mrr": round(sum(r["rr"] for r in rows) / len(rows), 3),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--modes", nargs="*", default=[m.value for m in Mode])
    args = p.parse_args()

    questions = load_questions()
    print(f"{len(questions)} questions ({sum(1 for q in questions if q['gold'])} with gold)\n")

    RESULTS.mkdir(parents=True, exist_ok=True)
    table = {}
    for name in args.modes:
        mode = Mode(name)
        print(f"running {mode} ...", flush=True)
        run = run_mode(mode, questions, args.top)
        summary = summarize(run, questions)
        table[str(mode)] = {**summary, "p50_ms": run["p50_ms"]}
        (RESULTS / f"retrieval_{mode}.json").write_text(
            json.dumps({"summary": summary, **run}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    k = args.top
    print(f"\n| Mode | Recall@{k} EN | JA | mixed | all | MRR | p50 ms |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for name, s in table.items():
        f = lambda d: "-" if d["recall"] is None else f"{d['recall']:.3f}"
        print(
            f"| {name} | {f(s['en'])} | {f(s['ja'])} | {f(s['mixed'])} "
            f"| **{f(s['all'])}** | {s['all']['mrr']:.3f} | {s['p50_ms']} |"
        )
    (RESULTS / "retrieval_summary.json").write_text(
        json.dumps(table, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
