"""Score the graded trap-set sheet into the headline table.

Reads eval/results/trapset_grading_sheet.jsonl once its `grade` fields are
filled in (correct | wrong | abstained), rejoins each row to its arm through
the key file, and prints the comparison.

Ungraded rows are reported and excluded rather than guessed at, so a partly
graded sheet gives a partial result instead of a wrong one.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
VALID = {"correct", "wrong", "abstained"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="run2", help="which run's sheet to score")
    args = p.parse_args()

    sheet_path = RESULTS / f"trapset_grading_sheet_{args.tag}.jsonl"
    key_path = RESULTS / f"trapset_key_{args.tag}.json"
    if not sheet_path.exists():
        print(f"No grading sheet for tag {args.tag!r}. Run: python eval/run_trapset.py")
        return 1

    key = json.loads(key_path.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in sheet_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    ungraded = [r["sheet_id"] for r in rows if r.get("grade") not in VALID]
    graded = [r for r in rows if r.get("grade") in VALID]
    if ungraded:
        print(f"{len(ungraded)} of {len(rows)} rows are not yet graded; excluding them.")
        print(f"  first few: {', '.join(ungraded[:8])}\n")
    if not graded:
        print("Nothing graded yet. Fill the 'grade' field with correct | wrong | abstained.")
        return 1

    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in graded:
        tally[key[r["sheet_id"]]["arm"]][r["grade"]] += 1

    print(f"| System | n | Wrong | Abstained | Correct | Error rate |")
    print("| --- | --- | --- | --- | --- | --- |")
    out = {}
    for arm, label in (("baseline", "Chat model, no retrieval"),
                       ("kotoba", "Kotoba (same model + retrieval)")):
        t = tally.get(arm)
        if not t:
            continue
        n = sum(t.values())
        wrong, abst, corr = t["wrong"], t["abstained"], t["correct"]
        # Error rate counts only answers actually given: abstaining is not an
        # error, it is a refusal to assert. The abstention column is reported
        # beside it so a high rate cannot hide behind a low error rate.
        answered = wrong + corr
        rate = wrong / answered if answered else 0.0
        out[arm] = {"n": n, "wrong": wrong, "abstained": abst, "correct": corr,
                    "error_rate_of_answers": round(rate, 3),
                    "error_rate_of_all": round(wrong / n, 3) if n else None}
        print(f"| {label} | {n} | {wrong} | {abst} | {corr} | **{rate:.1%}** |")

    (RESULTS / f"trapset_scores_{args.tag}.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("\nError rate is wrong / (wrong + correct): abstentions are excluded from")
    print("the denominator, since declining to answer is not an error. The")
    print("abstention count is reported alongside so it cannot hide there.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
