"""Retrieval modes compared in Phase 3, plus the JLPT rerank from Phase 6.

Modes: keyword (BM25 over ja.microsoft) | vector | hybrid | hybrid+semantic.
Keeping them behind one interface is what lets the eval harness sweep all four
without touching the rest of the system.
"""

from enum import StrEnum
from typing import Any


class Mode(StrEnum):
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"
    HYBRID_SEMANTIC = "hybrid_semantic"


def retrieve(
    query: str,
    mode: Mode = Mode.HYBRID,
    top: int = 5,
    jlpt_level: str | None = None,
) -> list[dict[str, Any]]:
    raise NotImplementedError("Phase 3")
