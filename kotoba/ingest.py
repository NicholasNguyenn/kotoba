"""Parse, chunk, JLPT-tag, embed, and upload the corpus. (Phase 1)

Embeddings are cached on disk by content hash: the catalog gets re-indexed many
times while patterns are tuned, and re-embedding it each time wastes credit.
"""


def run() -> None:
    raise NotImplementedError("Phase 1")


if __name__ == "__main__":
    run()
