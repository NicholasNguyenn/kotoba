"""Phase 0 acceptance check.

Proves four things before any real data exists:
  1. The embedding deployment answers and returns the dimensions we configured.
  2. The chat deployment answers (it is also the Phase 5 baseline model).
  3. We can create an index with a ja.microsoft field and a vector field.
  4. A query against that empty index succeeds.

It also probes whether the semantic ranker works on this search tier, which the
docs are ambiguous about for the Free tier. Run:

    python scripts/phase0_smoke.py
"""

from __future__ import annotations

import sys

from azure.core.exceptions import HttpResponseError

from kotoba.azure_clients import chat_client, embed
from kotoba.config import get_settings
from kotoba.search_index import build_index, index_client, search_client

PROBE_INDEX = "kotoba-phase0-probe"
SAMPLE = "猫が魚を食べた。"


def check_embedding() -> bool:
    s = get_settings()
    vectors = embed([SAMPLE])
    dims = len(vectors[0])
    ok = dims == s.embedding_dimensions
    print(f"  embedding: {dims} dims (expected {s.embedding_dimensions}) {'OK' if ok else 'MISMATCH'}")
    return ok


def check_chat() -> bool:
    s = get_settings()
    client = chat_client(s)
    response = client.chat.completions.create(
        model=s.azure_openai_chat_deployment,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        max_completion_tokens=16,
    )
    text = (response.choices[0].message.content or "").strip()
    print(f"  chat ({s.azure_openai_chat_deployment}): {text!r}")
    return bool(text)


def check_index_and_query() -> tuple[bool, bool]:
    """Returns (index_and_query_ok, semantic_ranker_available)."""
    s = get_settings()
    client = index_client(s)

    semantic_available = True
    try:
        client.create_or_update_index(build_index(PROBE_INDEX, s, with_semantic=True))
        print("  index: created with semantic configuration")
    except HttpResponseError as exc:
        print(f"  index: semantic configuration rejected ({exc.status_code}) -- retrying without")
        semantic_available = False
        client.create_or_update_index(build_index(PROBE_INDEX, s, with_semantic=False))
        print("  index: created without semantic configuration")

    searcher = search_client(PROBE_INDEX, s)
    results = list(searcher.search(search_text="猫", top=5))
    print(f"  keyword query on empty index: {len(results)} results (0 expected)")

    if semantic_available:
        try:
            list(
                searcher.search(
                    search_text="猫",
                    query_type="semantic",
                    semantic_configuration_name=s.semantic_config_name,
                    top=5,
                )
            )
            print("  semantic query: accepted -- semantic ranker usable on this tier")
        except HttpResponseError as exc:
            semantic_available = False
            print(f"  semantic query: REJECTED ({exc.status_code}) {exc.message.splitlines()[0]}")

    client.delete_index(PROBE_INDEX)
    print(f"  cleanup: deleted {PROBE_INDEX}")
    return True, semantic_available


def main() -> int:
    print("Phase 0 smoke test")
    print("- Azure OpenAI")
    emb_ok = check_embedding()
    chat_ok = check_chat()
    print("- Azure AI Search")
    search_ok, semantic = check_index_and_query()

    print()
    if emb_ok and chat_ok and search_ok:
        print("PASS: Phase 0 acceptance met.")
        if not semantic:
            print(
                "NOTE: semantic ranker unavailable here. Set "
                "AZURE_SEARCH_SEMANTIC_ENABLED=false and plan to run the "
                "hybrid+reranker mode on a short-lived Basic service in Phase 3."
            )
        return 0
    print("FAIL: see the mismatches above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
