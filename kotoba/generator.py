"""Cite-or-abstain prompting and output verification. (Phase 5)

Two jobs:
  - prompt the chat model so every claim carries a citation to a retrieved doc;
  - reject answers whose citations do not resolve, and abstain instead.

The same chat model, called with no retrieval and no citation rule, is the
Phase 5 baseline. Both paths go through `_complete` so they provably share the
model and the decoding parameters -- otherwise the comparison would be of
prompts and settings, not of retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from kotoba.azure_clients import chat_client
from kotoba.config import Settings, get_settings

ABSTAIN = "NOT_FOUND"
CITATION = re.compile(r"\[([a-zA-Z0-9\-]+)\]")

# Reasoning models spend part of this budget before emitting visible text.
MAX_COMPLETION_TOKENS = 1200

BASELINE_SYSTEM = (
    "You are a Japanese grammar tutor. Answer the learner's question in two to "
    "four sentences. Be specific and concrete."
)

KOTOBA_SYSTEM = "\n".join([
    "You are a Japanese grammar tutor. Answer ONLY from the evidence provided "
    "below. Every claim you make must be supported by that evidence, and you "
    "must cite the document it came from in square brackets, like [g-wa-001].",
    "",
    "If the evidence does not support an answer to the question, reply with "
    f"exactly {ABSTAIN} and nothing else. Do not answer from your own "
    "knowledge. A wrong answer is worse than no answer.",
    "",
    # Added after the first trap-set run: the model read a Tatoeba sentence
    # containing 窓が開いている and concluded ている was progressive there.
    # An example demonstrates a pattern without explaining it.
    "An example sentence shows a pattern being used; it does not explain it. "
    "Do not infer a grammatical rule from an example sentence alone. If the "
    f"only relevant evidence is example sentences, reply {ABSTAIN}.",
    "",
    # Also from that run: two English questions were answered in Japanese,
    # because the evidence is overwhelmingly Japanese and pulled the model
    # with it.
    "Answer in the SAME LANGUAGE as the question. If the learner asks in "
    "English, answer in English, even though the evidence is in Japanese.",
    "",
    "Answer in two to four sentences.",
])


@dataclass
class Answer:
    text: str
    citations: list[str] = field(default_factory=list)
    abstained: bool = False
    # Set when the model cited a document that was not in its evidence, which
    # is treated as an abstention: an unresolvable citation is not evidence.
    invalid_citations: list[str] = field(default_factory=list)


def _complete(system: str, user: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    response = chat_client(s).chat.completions.create(
        model=s.azure_openai_chat_deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )
    return (response.choices[0].message.content or "").strip()


def answer_without_retrieval(question: str, settings: Settings | None = None) -> Answer:
    """The baseline: same model, same decoding parameters, no evidence."""
    return Answer(text=_complete(BASELINE_SYSTEM, question, settings))


def format_evidence(docs: list[dict[str, Any]]) -> str:
    out = []
    for d in docs:
        body = " / ".join(x for x in (d.get("content_ja"), d.get("content_en")) if x)
        level = f" (JLPT {d['jlpt_level']})" if d.get("jlpt_level") else ""
        kind = d.get("doc_type", "")
        out.append(f"[{d['id']}] ({kind}{level}) {body}")
    return "\n".join(out)


def answer_with_evidence(
    question: str, evidence: list[dict[str, Any]], settings: Settings | None = None
) -> Answer:
    if not evidence:
        return Answer(text=ABSTAIN, abstained=True)

    user = f"Evidence:\n{format_evidence(evidence)}\n\nQuestion: {question}"
    text = _complete(KOTOBA_SYSTEM, user, settings)

    if text.strip().upper().startswith(ABSTAIN):
        return Answer(text=ABSTAIN, abstained=True)

    available = {d["id"] for d in evidence}
    cited = CITATION.findall(text)
    invalid = [c for c in cited if c not in available]

    # No citation at all means the claim is ungrounded, whatever it says; a
    # citation that does not resolve is worse, because it looks grounded.
    if not cited or invalid:
        return Answer(
            text=text, citations=[c for c in cited if c in available],
            abstained=True, invalid_citations=invalid,
        )

    return Answer(text=text, citations=cited)
