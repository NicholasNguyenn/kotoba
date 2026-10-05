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
| Semantic ranker on Free tier | **Uncertain** — the throttling table lists Basic and up only, while the overview says it can be used free "subject to free tier service limits" | [Semantic overview](https://learn.microsoft.com/en-us/azure/search/semantic-search-overview) |
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
