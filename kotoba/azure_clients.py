"""Thin constructors for the Azure clients, so tests can swap them out."""

from openai import AzureOpenAI

from kotoba.config import Settings, get_settings


def embedding_client(settings: Settings | None = None) -> AzureOpenAI:
    s = settings or get_settings()
    s.require("azure_openai_endpoint", "azure_openai_api_key")
    return AzureOpenAI(
        azure_endpoint=s.azure_openai_endpoint,
        api_key=s.azure_openai_api_key,
        api_version=s.azure_openai_api_version,
    )


# The chat and embedding clients are identical today, but the baseline run in
# Phase 5 must use the same chat model as Kotoba, so it gets its own name to
# make that explicit at the call sites.
chat_client = embedding_client


def embed(texts: list[str], settings: Settings | None = None) -> list[list[float]]:
    """Embed a batch of strings. Batching matters: Phase 1 embeds thousands."""
    s = settings or get_settings()
    client = embedding_client(s)
    response = client.embeddings.create(
        model=s.azure_openai_embedding_deployment,
        input=texts,
        dimensions=s.embedding_dimensions,
    )
    return [item.embedding for item in response.data]
