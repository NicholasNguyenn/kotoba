"""Run the trap set through both arms and emit a blind grading sheet.

Both arms are in one script, rather than the separate run_baseline.py and
run_kotoba.py of the original layout, so that a single pass provably uses the
same model, the same decoding parameters and the same cases for both. Keeping
them apart invites drift between the two.

    python eval/run_trapset.py              both arms, then the grading sheet
    python eval/run_trapset.py --arm kotoba

Grading is deliberately NOT automated. The sheet is shuffled and the system
names are hidden, so the grader cannot tell which arm produced an answer.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kotoba.generator import answer_with_evidence, answer_without_retrieval  # noqa: E402
from kotoba.retriever import Mode, retrieve  # noqa: E402

TRAP_SET = ROOT / "eval" / "trap_set.jsonl"
RESULTS = ROOT / "eval" / "results"
SHUFFLE_SEED = 20261005


def load_cases() -> list[dict]:
    return [json.loads(l) for l in TRAP_SET.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_baseline(cases: list[dict]) -> list[dict]:
    out = []
    for i, c in enumerate(cases, 1):
        a = answer_without_retrieval(c["question"])
        out.append({"id": c["id"], "arm": "baseline", "text": a.text,
                    "citations": [], "abstained": False})
        print(f"  baseline {i}/{len(cases)}", flush=True)
    return out


def run_kotoba(cases: list[dict], top: int = 5) -> list[dict]:
    out = []
    for i, c in enumerate(cases, 1):
        docs = retrieve(c["question"], mode=Mode.HYBRID_SEMANTIC, top=top)
        a = answer_with_evidence(c["question"], docs)
        out.append({"id": c["id"], "arm": "kotoba", "text": a.text,
                    "citations": a.citations, "abstained": a.abstained,
                    "invalid_citations": a.invalid_citations,
                    "retrieved": [d["id"] for d in docs]})
        print(f"  kotoba {i}/{len(cases)}", flush=True)
    return out


def write_grading_sheet(cases: list[dict], answers: list[dict]) -> Path:
    by_case = {c["id"]: c for c in cases}
    items = []
    for a in answers:
        c = by_case[a["id"]]
        items.append({
            "sheet_id": None,
            "case_id": a["id"],
            "arm": a["arm"],
            "question": c["question"],
            "reference_answer": c["correct"],
            "common_error": c["common_error"],
            "expect": c["expect"],
            "answer": a["text"],
            "abstained": a["abstained"],
            "grade": "",  # correct | wrong | abstained
        })
    random.Random(SHUFFLE_SEED).shuffle(items)
    for n, it in enumerate(items, 1):
        it["sheet_id"] = f"s-{n:03d}"

    RESULTS.mkdir(parents=True, exist_ok=True)
    key = RESULTS / "trapset_key.json"
    key.write_text(json.dumps(
        {it["sheet_id"]: {"case_id": it["case_id"], "arm": it["arm"]} for it in items},
        indent=2), encoding="utf-8")

    sheet = RESULTS / "trapset_grading_sheet.jsonl"
    sheet.write_text("\n".join(
        json.dumps({k: v for k, v in it.items() if k != "arm"}, ensure_ascii=False)
        for it in items) + "\n", encoding="utf-8")
    return sheet


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--arm", choices=["baseline", "kotoba", "both"], default="both")
    args = p.parse_args()

    cases = load_cases()
    print(f"{len(cases)} trap cases "
          f"({sum(1 for c in cases if c['expect'] == 'answer')} expect an answer, "
          f"{sum(1 for c in cases if c['expect'] == 'abstain')} expect abstention)\n")

    RESULTS.mkdir(parents=True, exist_ok=True)
    answers: list[dict] = []
    if args.arm in ("baseline", "both"):
        answers += run_baseline(cases)
    if args.arm in ("kotoba", "both"):
        answers += run_kotoba(cases)

    (RESULTS / f"trapset_answers_{args.arm}.jsonl").write_text(
        "\n".join(json.dumps(a, ensure_ascii=False) for a in answers) + "\n", encoding="utf-8")

    kot = [a for a in answers if a["arm"] == "kotoba"]
    if kot:
        n_abs = sum(1 for a in kot if a["abstained"])
        n_bad = sum(1 for a in kot if a.get("invalid_citations"))
        print(f"\nkotoba abstained on {n_abs}/{len(kot)}"
              f" ({n_bad} of those for unresolvable citations)")

    if args.arm == "both":
        sheet = write_grading_sheet(cases, answers)
        print(f"\nblind grading sheet: {sheet}")
        print("Grade each 'grade' field as correct | wrong | abstained, then run")
        print("  python eval/score_trapset.py")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
