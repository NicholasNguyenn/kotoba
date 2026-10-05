"""SudachiPy wrapper. (Phase 4)

Named `tokenizer.py`, not `tokenize.py`, to avoid confusion with the standard
library module of that name.

Grammar matching needs the dictionary form and part of speech, not the surface
string: 食べなかった must still match the ～なかった pattern.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    surface: str
    lemma: str
    pos: str
    reading: str


def tokenize(text: str) -> list[Token]:
    raise NotImplementedError("Phase 4")
