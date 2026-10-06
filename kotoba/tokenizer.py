"""SudachiPy wrapper.

Named `tokenizer.py`, not `tokenize.py`, to avoid confusion with the standard
library module of that name.

Grammar matching needs the dictionary form and part of speech, not the surface
string: 食べなかった must still match a pattern written as ない.
"""

from dataclasses import dataclass
from functools import lru_cache

from sudachipy import dictionary
from sudachipy import tokenizer as _sudachi


@dataclass(frozen=True)
class Token:
    surface: str
    lemma: str
    pos: str
    reading: str


@lru_cache(maxsize=1)
def _tokenizer():
    # Loading the dictionary costs ~1s, so hold exactly one.
    return dictionary.Dictionary(dict="core").tokenizer()


def tokenize(text: str) -> list[Token]:
    # SplitMode.C = longest units, which keeps compound expressions intact.
    return [
        Token(m.surface(), m.dictionary_form(), m.part_of_speech()[0], m.reading_form())
        for m in _tokenizer().tokenize(text, _sudachi.Tokenizer.SplitMode.C)
    ]
