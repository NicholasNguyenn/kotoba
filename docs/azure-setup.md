# Azure setup for Kotoba

Verified against Microsoft's docs on 2026-10-05. Anything marked **uncertain**
is resolved empirically by `scripts/phase0_smoke.py` rather than guessed.

## What the current limits actually are

| Thing | Value | Source |
| --- | --- | --- |
| Search **Free** tier storage | 50 MB, 3 indexes, 1 service per subscription | [Service limits](https://learn.microsoft.com/en-us/azure/search/search-limits-quotas-capacity) |
| Free-tier vector search | Supported; storage is the real constraint | [Vector quickstart](https://learn.microsoft.com/en-us/azure/search/search-get-started-vector) |
| Free-tier idle deletion | A free service "might be deleted after extended periods of inactivity" | Service limits |
| Semantic ranker free allowance | First 1,000 requests/month free (the default "free plan") | [Enable/disable billing](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-enable-disable) |
| Semantic ranker on Free tier | **Confirmed by running it** (2026-10-05): a semantic query against a Free-tier Canada Central service was accepted. The region table footnotes which regions support it on free; Canada Central is one | [Region support](https://learn.microsoft.com/en-us/azure/search/search-region-support) + `scripts/phase0_smoke.py` |
| Azure for Students credit | $100, 12 months, no credit card | [Offer details](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/) |
| Azure OpenAI access request | No longer required for standard models | [Limited access](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/limited-access) |
| Azure OpenAI on student subscriptions | **Uncertain** — not excluded in the official offer terms, but repeatedly reported as blocked in Microsoft Q&A | see below |

Two naming changes since the project was planned: the portal now presents this
as **Microsoft Foundry** (ai.azure.com) rather than Azure OpenAI Studio, and a
new **Serverless Developer** search tier entered preview (billing began
2026-09-13) with consumption pricing and semantic ranker support.

## Known caveats

**Python 3.14 is fine.** Tested 2026-10-05: `pydantic-settings`, `openai`,
`azure-search-documents`, `fastapi`, `mcp`, and `sudachipy` + `sudachidict-core`
all install as wheels on cp314, and tokenization works. No 3.12 downgrade needed.

**Windows console encoding.** Printing Japanese fails with
`UnicodeEncodeError: 'charmap' codec` because the console defaults to cp1252.
Set `PYTHONUTF8=1` (or `$env:PYTHONUTF8=1`) when running any script that prints
Japanese. This is a console issue only, not a tokenizer or data issue.

**Semantic ranker and the fourth retrieval mode.** The hybrid+reranker row of
the results table needs semantic ranking. If the Free tier rejects it, the plan
is a short-lived Basic service for the Phase 3 run only: Basic is billed hourly,
so one afternoon is a couple of dollars rather than a month's $75+. Record which
tier produced each row in `eval/results/`.

## Region decision (this subscription)

Azure for Students pins this subscription to five regions by policy
(`RequestDisallowedByAzure` otherwise):
`canadacentral, germanywestcentral, belgiumcentral, swedencentral, mexicocentral`.

Find them at Portal -> Policy -> Authoring -> Assignments -> "Allowed resource
deployment regions" -> Parameters. The set is per-subscription.

Cross-referencing both services against that list:

| Region | Chat model | Embeddings | Search | Semantic ranker on Free |
| --- | --- | --- | --- | --- |
| **swedencentral** | gpt-5-mini, gpt-5-nano, gpt-4o-mini, gpt-4.1-mini | yes | creation blocked (high demand) | yes, if creatable |
| germanywestcentral | same as above | yes | creation blocked (high demand) | yes, if creatable |
| **canadacentral** | **none** | yes | **available** | **yes** |
| mexicocentral | no Azure OpenAI | no | available | no |
| belgiumcentral | no Azure OpenAI | no | not offered | n/a |

**Decision: a split deployment.**

- **Azure OpenAI -> Sweden Central.** The only allowed regions with a small chat
  model are Sweden Central and Germany West Central. Verified Global Standard:
  `gpt-5-mini`, `gpt-5-nano`, `gpt-4o-mini`, `gpt-4.1-mini`,
  `text-embedding-3-small`.
- **Azure AI Search -> Canada Central.** It supports the semantic ranker *on the
  Free tier*, and unlike Sweden Central and Germany West Central it is not
  flagged as capacity-blocked for new services.

Two consequences:

**The fourth retrieval mode is free.** No Basic service is needed for the
hybrid+reranker row after all. The semantic ranker free plan allows 1,000
requests/month; Phase 3 needs ~75 semantic queries per sweep, so there is room
to re-run many times.

**Different regions is fine here, and it is a deliberate choice.** Same-region
coexistence is required only for *AI enrichment* -- skillsets where Search calls
the embedding model itself (integrated vectorization). Kotoba embeds in
`ingest.py` and pushes vectors, so that dependency never applies.

The cost is network: the online path embeds a query in Sweden, searches in
Canada, and generates in Sweden, so p50 latency carries two transatlantic hops.
Phase 6 must report latency with that geography stated, and the obvious
optimization is to overlap the keyword leg with the query-embedding call (or
cache query embeddings) rather than run them in sequence.

## Phase 0 result

`scripts/phase0_smoke.py` passed on 2026-10-05:

```
embedding: 1536 dims (expected 1536) OK
chat (gpt-5-mini): 'ready' [finish_reason=stop]
index: created with semantic configuration
keyword query on empty index: 0 results (0 expected)
semantic query: accepted -- semantic ranker usable on this tier
```

So `AZURE_SEARCH_SEMANTIC_ENABLED=true` stands, and the hybrid+reranker row of
the Phase 3 table needs no paid tier.

One trap worth remembering: the search service was deleted and recreated to get
off the Standard tier that the Foundry IQ flow provisioned ($249.98/month).
Admin keys do not survive that, so a key copied before the recreate authenticates
as garbage.

## Measured index capacity (2026-10-05)

| Documents | Storage used | Quota | Per doc |
| --- | --- | --- | --- |
| 2,914 @ 1536 dims | over quota | 50 MB | ~17 KB |
| 2,914 @ 512 dims | 11.5 MB | 50 MB | ~3.9 KB |

At 1536 dimensions the corpus did not fit: the reported usage lagged at 41.6 MB
and then adding two documents was rejected with `Storage quota has been
exceeded`. Do not trust the storage counter as a live gauge; it trails reality.

At 512 dimensions the same 2,914 documents occupy 11.5 MB (22%), leaving room
for roughly 9,000 more. `text-embedding-3-small` is trained for this reduction.
All retrieval modes share the same embedding, so the comparison between them is
unaffected; the absolute recall@5 figures are reported alongside the dimension
count.

Uploads must be batched small. At 100 documents per request the payload is
~3 MB of JSON floats and the Free tier resets the connection
(`ConnectionResetError 10054`) partway through; 25 per request succeeded with
zero retries. `--resume` skips documents already indexed.
