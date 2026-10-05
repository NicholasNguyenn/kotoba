"""Cite-or-abstain prompting and output verification. (Phase 5)

Two jobs:
  - prompt the chat model so every claim carries a citation to a retrieved doc;
  - reject answers whose citations do not resolve, and abstain instead.

The same chat model, called with no retrieval and no citation rule, is the
Phase 5 baseline. Both paths must share this module's model settings so the
comparison is of retrieval, not of decoding parameters.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Answer:
    text: str
    citations: list[str]
    abstained: bool


def answer_with_evidence(question: str, evidence: list[dict[str, Any]]) -> Answer:
    raise NotImplementedError("Phase 5")


def answer_without_retrieval(question: str) -> Answer:
    """The baseline: same model, same decoding parameters, no evidence."""
    raise NotImplementedError("Phase 5")
