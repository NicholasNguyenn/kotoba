# Kotoba — handoff

Written 2026-10-05. Picks up mid-Phase-5. Repo:
<https://github.com/NicholasNguyenn/kotoba> · last commit `5847640`.

Kotoba is a Japanese reading companion that grounds every grammar explanation
in retrieved evidence. It exists to produce **measured numbers for a Microsoft
SWE intern application**, so the governing rule is: *every number in the README
and on the resume must come from a committed run.* Never estimate, never round
up, never fill a placeholder with a plausible figure.

---

## Where things stand

| Phase | State | Number produced |
| --- | --- | --- |
| 0 Setup | done | — |
| 1 Data | done (catalog is 14 of a planned ~100 entries) | — |
| 2 Eval sets | questions + passages frozen; trap set written | — |
| 3 Retrieval | **done** | recall@5 **0.821 → 0.923** |
| 4 Detection | **done** | precision **0.933**, recall **1.000** |
| 5 Trap set | **in progress** — see "Next action" | A%, B% not yet produced |
| 6 Rerank / MCP / latency | not started | Z ms |
| 7 README / resume | not started | — |

### Next action (start here)

A background run of `python eval/run_trapset.py --arm both` was in flight when
this was written. It may have completed, been interrupted, or written partial
files.

1. Check whether `eval/results/trapset_grading_sheet.jsonl` exists and holds
   70 rows (35 cases × 2 arms).
2. If not, re-run it. It costs about 70 chat calls, a few cents:
   ```
   python eval/run_trapset.py --arm both
   ```
3. **The human grades the sheet.** Fill each row's `grade` field with
   `correct`, `wrong`, or `abstained`. The sheet is shuffled under a fixed seed
   and the arm is stripped out into `trapset_key.json`, so the grader cannot
   tell which system produced an answer. Do not undo that, and do not grade it
   with a model — the credibility of the headline number rests on it.
4. Then:
   ```
   python eval/score_trapset.py
   ```
   which prints the headline table and writes `trapset_scores.json`.
5. Put that table in the README next to the others.

**Do not** let an agent fill in the `grade` fields. If an LLM-judged
preliminary pass is wanted, it must be run as a *separate*, clearly labeled
column, never substituted for the human grading.

---

## Expected finding, so it is not mistaken for a bug

The Kotoba arm abstained on **17 of 35** cases. Of the 8 over-abstentions
(cases the catalog was expected to cover), **6 had the correct catalog entry in
the retrieved evidence** and the model still declined.

That is correct behaviour, not a defect. The questions are comparative —
"だけ vs しか", "なければならない vs なくてもいい", "ことができる vs ことがある"
— and a 14-entry catalog only holds one side of each comparison. The
cite-or-abstain rule is working exactly as designed.

The consequence for the write-up: Kotoba's error rate should come out low while
its abstention rate is high, and **that trade-off is the honest result**. The
lever that converts abstentions into correct answers is growing the catalog,
not loosening the prompt. Loosening the prompt to reduce abstentions would
manufacture a better-looking number by removing the thing that makes the
project worth anything.

---

## Hard-won facts that are not obvious from the code

**Azure for Students is region-locked by policy.** This subscription allows
only `canadacentral, germanywestcentral, belgiumcentral, swedencentral,
mexicocentral`. Anything else fails with `RequestDisallowedByAzure`. The list
is per-subscription: Portal → Policy → Authoring → Assignments → "Allowed
resource deployment regions" → Parameters.

**The deployment is deliberately split across two regions.** Azure OpenAI is in
**Sweden Central** (the only allowed region with a small chat model); Azure AI
Search is in **Canada Central** (the only allowed region where Search is
creatable *and* supports the semantic ranker on the Free tier). This is legal
only because ingestion embeds client-side and pushes vectors — same-region
coexistence is required only for integrated vectorization, which is not used.
Do not "tidy" this into one region; it would cost either the chat model or the
free reranker.

**The semantic ranker is free here.** Free-tier semantic ranking is supported
per-region and Canada Central is one of those regions; confirmed by running it,
not just by reading docs. No Basic tier is needed. Free allowance is 1,000
semantic requests/month; a Phase 3 sweep uses ~83.

**Embeddings are 512-dim, not 1536.** At 1536 the 2,914-document corpus
exceeded the Free tier's 50 MB outright. At 512 it uses 11.5 MB. Changing this
changes recall@5, so it must not be changed now that the eval sets are frozen
and Phase 3 is measured. If it ever changes, Phase 3 must be re-run and both
numbers published.

**The storage counter lags badly.** It reported 41.6 MB right up until an
upload was rejected for exceeding a 50 MB quota. Do not trust it as a live
gauge.

**Upload batches must be small.** 100 documents per request is ~3 MB of JSON
floats and the Free tier resets the connection partway (`ConnectionResetError
10054`). `UPLOAD_BATCH = 25` runs clean. `--resume` skips documents already
indexed.

**Search admin keys do not survive deleting and recreating the service.** The
service was recreated once (the Foundry IQ flow had provisioned **Standard at
$249.98/month** instead of Free — check the tier on any new search service).

**The Foundry portal shows the endpoint as `.../openai/v1`.** The `AzureOpenAI`
client wants the bare origin; `config.py` strips the suffix so either form
works in `.env`.

**Windows console:** set `PYTHONUTF8=1` or any script printing Japanese dies
with `UnicodeEncodeError: 'charmap'`. Scripts call
`sys.stdout.reconfigure(line_buffering=True)` because stdout block-buffers when
redirected and long runs otherwise appear to hang.

**`gpt-5-mini` is a reasoning model.** It spends part of the completion budget
on hidden reasoning before emitting visible text, so a small
`max_completion_tokens` returns empty content that looks like a dead endpoint.

---

## Methodology rules that must not be relaxed

These are what make the numbers worth putting on a resume.

1. **Eval sets are frozen.** `eval/questions.jsonl`, `eval/passages.jsonl` and
   `eval/trap_set.jsonl` are committed and must not be edited in response to
   results. Fixing *code* after seeing results is fine; editing *labels* is
   not.
2. **Passage labels were assigned by reading, never by running the detector.**
   Labelling with the detector would make precision 100% by construction. 22 of
   the 30 passages carry deliberate lookalikes (`とても` containing ても,
   `だけど` containing だけ, sentence-initial でも, conjunctive が, purpose-のに).
3. **One known label error is left uncorrected.** Passage `p-008` contains a
   genuine subject-marker が that the labels miss, so detection precision is
   reported slightly *below* the truth. Every label edited after the fact
   favours the system, so it was left alone and under-claimed.
4. **Detection precision 0.933 is post-hoc** — measured at 0.871, then three
   root-cause defects were fixed, then re-measured. Both numbers are in the
   README and the post-hoc nature is stated. Do not quietly drop the 0.871.
5. **Trap-set grading is blind and human.** See "Next action".
6. **The catalog is unverified.** All 14 entries carry `verified: false`.
   `docs/catalog-review.md` is generated for a textbook pass. Until those flags
   flip, the catalog is seed data, not evidence. `unverified()` in
   `grammar_detect.py` reports them.

---

## Known defects, deliberately unfixed

**`のに` is always labelled "even though".** The purpose sense (`駅に着くのに
30分かかる`, "it takes 30 minutes to get to the station") is mislabelled. Three
of the four remaining detection false positives are this. It is not reliably
separable from the concessive sense with the information the tokenizer gives.
Measured and reported rather than hidden.

**Six retrieval questions still miss, mostly romaji** (`bakari`, `koto ga
dekiru`, `teshimau`). Nothing in the index is written in romaji, so neither
BM25 nor the embedding has a bridge. Adding a romaji reading field would likely
fix all six — but that changes the index, so it requires a **full Phase 3
re-run and a separate row in the results table**. Do not fix it and then
publish the existing numbers.

Shortcuts taken on purpose are marked with `ponytail:` comments in the source;
`grep -rn "ponytail:"` lists them.

---

## What remains

**Finish Phase 5** (above) → fills N, A%, B%.

**Phase 4 remainder:** `/breakdown` endpoint in `kotoba/api.py`. Tokenize,
detect catalog points, let the LLM propose candidates, keep only those
`confirm_candidates()` confirms. `api.py` currently has `/health` only.

**Phase 6:** JLPT reranking is already implemented in `retriever.py`
(`_jlpt_rerank`) but is unmeasured. The MCP server
(`kotoba/mcp_server.py`) is a stub. Latency: keyword-only p50 is **902 ms**
and the three embedding modes are **~1670 ms**; that ~770 ms delta is the
Sweden embedding round-trip made sequentially before the Canada search. The
obvious optimization is overlapping the two, which gives a real before/after
for the Z ms bullet.

**Phase 7:** README is current for Phases 3 and 4. Needs the Phase 5 table, a
side-by-side of a baseline mistake against Kotoba's cited answer, and a demo
GIF. The resume bullets in the original handoff doc still hold except that N is
35, not ~50.

**Growing the catalog** toward ~100 entries is the single highest-leverage
task: it drives the abstention rate down, makes the trap set expandable past 35
cases, and is the only lever that improves Phase 5 honestly. Each entry costs
~4 KB indexed and there is ~38 MB of headroom. After editing the catalog, run
`python -m kotoba.ingest --resume` to index new entries.

---

## Running it

```
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env     # fill 3 values; see docs/azure-setup.md
PYTHONUTF8=1 python scripts/phase0_smoke.py   # verifies Azure end to end
pytest -q                                      # 21 tests, all offline
```

| Command | Purpose |
| --- | --- |
| `python -m kotoba.ingest --download` | fetch JMdict + Tatoeba (~31 MB) |
| `python -m kotoba.ingest [--resume]` | build, embed, upload corpus |
| `python eval/run_retrieval.py` | Phase 3 table (~83 queries × 4 modes) |
| `python eval/run_detection.py` | Phase 4 precision/recall |
| `python eval/run_trapset.py --arm both` | Phase 5 both arms + grading sheet |
| `python eval/score_trapset.py` | Phase 5 headline table, after grading |

`.env` is gitignored and holds three secrets: the Azure OpenAI endpoint and
key, and the Search admin key. Deployments are named `gpt-5-mini` and
`text-embedding-3-small`; those exact strings are passed as the `model`
parameter.
