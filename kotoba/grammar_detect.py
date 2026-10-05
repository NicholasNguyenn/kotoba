"""Match tokens to catalog patterns, and verify LLM-proposed candidates. (Phase 4)

The rule that makes Kotoba's numbers meaningful: the LLM may *propose* grammar
points, but only points confirmed against a catalog entry survive.
"""

from dataclasses import dataclass

from kotoba.tokenizer import Token


@dataclass(frozen=True)
class DetectedPoint:
    catalog_id: str
    pattern: str
    span: tuple[int, int]
    confirmed: bool


def detect(tokens: list[Token]) -> list[DetectedPoint]:
    raise NotImplementedError("Phase 4")


def confirm_candidates(candidates: list[str], tokens: list[Token]) -> list[DetectedPoint]:
    raise NotImplementedError("Phase 4")
