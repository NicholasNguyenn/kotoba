"""Tests that need no Azure credentials."""

import pytest

from kotoba.config import Settings
from kotoba.search_index import build_index


def test_require_reports_missing_settings():
    settings = Settings(azure_search_endpoint="", azure_search_api_key="")
    with pytest.raises(RuntimeError, match="azure_search_endpoint"):
        settings.require("azure_search_endpoint")


def test_index_uses_japanese_analyzer_and_vector_dims():
    settings = Settings(azure_search_index="t", embedding_dimensions=1536)
    index = build_index(settings=settings, with_semantic=True)
    by_name = {f.name: f for f in index.fields}

    assert by_name["content_ja"].analyzer_name == "ja.microsoft"
    assert by_name["embedding"].vector_search_dimensions == 1536
    assert index.semantic_search is not None


def test_semantic_can_be_omitted():
    settings = Settings(azure_search_index="t")
    assert build_index(settings=settings, with_semantic=False).semantic_search is None
