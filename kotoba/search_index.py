"""Index schema for Kotoba.

One index, not three. The Free tier allows only 3 indexes and 50 MB total, and
a single index with a `doc_type` discriminator lets a query reach the grammar
catalog, JMdict entries, and Tatoeba sentences in one round trip -- which is
what recall@5 in Phase 3 is actually measuring.

Japanese and English text live in separate fields so each can get the right
analyzer: `ja.microsoft` segments Japanese (there are no spaces to split on),
`en.microsoft` stems English.
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from kotoba.config import Settings, get_settings

HNSW_CONFIG_NAME = "kotoba-hnsw"
VECTOR_PROFILE_NAME = "kotoba-vector-profile"


def index_client(settings: Settings | None = None) -> SearchIndexClient:
    s = settings or get_settings()
    s.require("azure_search_endpoint", "azure_search_api_key")
    return SearchIndexClient(
        endpoint=s.azure_search_endpoint,
        credential=AzureKeyCredential(s.azure_search_api_key),
    )


def search_client(
    index_name: str | None = None, settings: Settings | None = None
) -> SearchClient:
    s = settings or get_settings()
    s.require("azure_search_endpoint", "azure_search_api_key")
    return SearchClient(
        endpoint=s.azure_search_endpoint,
        index_name=index_name or s.azure_search_index,
        credential=AzureKeyCredential(s.azure_search_api_key),
    )


def build_index(
    index_name: str | None = None,
    settings: Settings | None = None,
    with_semantic: bool | None = None,
) -> SearchIndex:
    """Construct the index definition.

    `with_semantic` is separable because the semantic ranker may not be
    available on the Free tier; the Phase 0 probe decides empirically.
    """
    s = settings or get_settings()
    name = index_name or s.azure_search_index
    semantic = s.azure_search_semantic_enabled if with_semantic is None else with_semantic

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(
            name="doc_type",  # grammar | entry | sentence
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SearchableField(
            name="pattern",  # the grammar form itself, e.g. ～ばかり
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
        ),
        SearchableField(
            name="content_ja",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",
        ),
        SearchableField(
            name="content_en",
            type=SearchFieldDataType.String,
            analyzer_name="en.microsoft",
        ),
        SimpleField(
            name="jlpt_level",  # N5..N1, drives the Phase 6 rerank
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(name="source", type=SearchFieldDataType.String, retrievable=True),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            retrievable=False,
            vector_search_dimensions=s.embedding_dimensions,
            vector_search_profile_name=VECTOR_PROFILE_NAME,
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=HNSW_CONFIG_NAME)],
        profiles=[
            VectorSearchProfile(
                name=VECTOR_PROFILE_NAME,
                algorithm_configuration_name=HNSW_CONFIG_NAME,
            )
        ],
    )

    semantic_search = None
    if semantic:
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name=s.semantic_config_name,
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="pattern"),
                        content_fields=[
                            SemanticField(field_name="content_ja"),
                            SemanticField(field_name="content_en"),
                        ],
                    ),
                )
            ]
        )

    return SearchIndex(
        name=name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )


def create_or_update_index(
    index_name: str | None = None,
    settings: Settings | None = None,
    with_semantic: bool | None = None,
) -> SearchIndex:
    client = index_client(settings)
    return client.create_or_update_index(
        build_index(index_name, settings, with_semantic)
    )
