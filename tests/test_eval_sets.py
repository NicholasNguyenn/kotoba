"""Guards on the frozen eval sets.

These exist because a gold id that does not resolve makes recall@5 silently
unachievable for that question, which would understate every retrieval mode
equally and look like a real result.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _jsonl(path):
    return [json.loads(l) for l in (ROOT / path).read_text(encoding="utf-8").splitlines() if l.strip()]


def test_every_gold_id_exists_in_the_corpus():
    corpus = {d["id"] for d in _jsonl("data/processed/corpus.jsonl")}
    unresolved = {
        q["id"]: [g for g in q["gold"] if g not in corpus] for q in _jsonl("eval/questions.jsonl")
    }
    assert not {k: v for k, v in unresolved.items() if v}


def test_question_ids_and_queries_are_unique():
    qs = _jsonl("eval/questions.jsonl")
    assert len({q["id"] for q in qs}) == len(qs)
    assert len({q["query"] for q in qs}) == len(qs)


def test_question_set_covers_the_required_splits():
    qs = _jsonl("eval/questions.jsonl")
    langs = {q["lang"] for q in qs}
    assert langs == {"en", "ja", "mixed"}
    assert sum(1 for q in qs if not q["gold"]) >= 5, "need abstention cases"
    assert sum(1 for q in qs if q["note"] == "romaji") >= 5
    assert sum(1 for q in qs if q["note"] == "kana-only") >= 5
