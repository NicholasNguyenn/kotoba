# Kotoba

A Japanese reading companion. Paste a passage; Kotoba breaks it into grammar
points and backs every explanation with retrieved evidence — a hand-built
grammar catalog, JMdict, and Tatoeba — instead of trusting a language model's
unsupported claim. When nothing in its sources supports a point, it says so
rather than guessing.

General LLMs explain Japanese grammar confidently and are sometimes wrong, and
a learner cannot tell which is which. The headline measurement here is the
explanation error rate for **the same chat model with and without Kotoba's
retrieval**, on a frozen set of tricky grammar cases.

## Status

Phase 3 of 7. Retrieval comparison measured; the explanation-error headline
(Phase 5) is not yet.

- [x] 0 · Setup: Azure resources, repo skeleton, smoke test
- [ ] 1 · Data: ~100-point grammar catalog (N5–N3), JMdict, Tatoeba
      *(12 seed entries + lemma matching done; all unverified)*
- [x] 2 · Eval sets, frozen before any tuning
- [x] 3 · Retrieval: keyword / vector / hybrid / hybrid+reranker
- [ ] 4 · Reading breakdown
- [ ] 5 · Plain LLM vs Kotoba on the trap set
- [ ] 6 · JLPT reranking, MCP tools, latency
- [ ] 7 · Polish

## Results

Both tables are published empty on purpose. Numbers land here only when a
committed run under `eval/results/` produces them.

### Explanation errors on the trap set (Phase 5)

| System | Wrong | Abstained | Correct |
| --- | --- | --- | --- |
| Chat model, no retrieval | — | — | — |
| Kotoba (same model + retrieval) | — | — | — |

### Retrieval mode comparison, recall@5 (Phase 3)

78 questions with gold documents over a 2,914-document index, 512-dim
embeddings. Recall@5 is "did any gold document land in the top 5".

| Mode | EN | JA | Mixed | **All** | MRR | p50 ms |
| --- | --- | --- | --- | --- | --- | --- |
| Keyword (BM25, `ja.microsoft`) | 0.686 | 0.938 | 0.909 | **0.821** | 0.786 | 902 |
| Vector only | 0.829 | 0.938 | 0.909 | **0.885** | 0.825 | 1675 |
| Hybrid | 0.829 | 0.969 | 0.909 | **0.897** | 0.852 | 1668 |
| Hybrid + semantic reranker | 0.886 | 0.969 | 0.909 | **0.923** | 0.863 | 1706 |

**Recall@5 rises from 0.821 to 0.923**, and essentially all of the gain is on
English queries (0.686 to 0.886). Japanese queries start high because BM25 with
the `ja.microsoft` analyzer already matches Japanese text well; English queries
have to reach Japanese documents through terse glosses, which is what the
embeddings fix. Splitting the eval by language is what makes that visible —
the aggregate alone would have hidden it.

The 6 questions the best mode still misses are mostly **romaji** grammar
queries (`bakari`, `koto ga dekiru`, `teshimau`): nothing in the index is
written in romaji, so neither BM25 nor the embedding has a bridge to it. Adding
a romaji reading field is the obvious fix, and would be reported as a separate
re-run rather than folded into these numbers.

Retrieval always returns its top k, so the 5 abstention questions all return
something here. Deciding that the evidence does not support an answer is the
generator's job, measured in Phase 5 — not retrieval's.

## Design notes

**One index, not three.** The grammar catalog, JMdict entries, and Tatoeba
sentences share a single index with a `doc_type` discriminator. The Free search
tier allows 3 indexes and 50 MB total, and a single index lets one query reach
all three sources — which is what recall@5 measures.

**Separate fields per language.** `content_ja` uses the `ja.microsoft`
analyzer (Japanese has no spaces to split on) and `content_en` uses
`en.microsoft`. The eval set is tagged `en` / `ja` / `mixed` so the comparison
can show where each retrieval mode actually helps.

**The catalog has the final say.** The LLM may propose grammar points; only
points confirmed against a catalog entry survive into the output. That rule is
what makes the Phase 5 comparison about retrieval rather than about prompting.

**SudachiPy over fugashi.** Both were on the table; SudachiPy installs as a
wheel with no MeCab build chain, which on Windows + Python 3.14 is the
difference between working and not. It also gives the dictionary form directly:
`食べなかった` segments to `食べる + ない + た`, so patterns can match the lemma
rather than the surface string.

**Pasted passages are never stored or indexed**, so copyrighted articles stay
out of the corpus.

## Setup

Verified on Python 3.14 (Windows). Japanese output needs UTF-8 on a Windows
console, so set `PYTHONUTF8=1` or the console will raise `UnicodeEncodeError`
when printing kanji.

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
cp .env.example .env                              # then fill in your Azure values
python scripts/phase0_smoke.py
```

`docs/azure-setup.md` has the verified resource walkthrough, current free-tier
limits, and the cost notes.

## Data and attribution

| Source | Use | License |
| --- | --- | --- |
| Grammar catalog | Core evidence, ~100 points N5–N3 | Written for this project from my own notes |
| [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) (via `jmdict-simplified`) | Dictionary entries | CC BY-SA 4.0 (EDRDG) |
| [Tatoeba](https://tatoeba.org/) | Example sentences | CC BY 2.0 FR |

JLPT level tags come from a separately licensed list, recorded in
`data/processed/` provenance fields when Phase 1 lands.
