"""FastAPI surface. (Phase 4)

/health works now so the container is verifiable before the rest exists.
Pasted passages are never persisted or indexed.
"""

from fastapi import FastAPI

from kotoba import __version__

app = FastAPI(title="Kotoba", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


# /breakdown  -> Phase 4
# /ask        -> Phase 5
# /search     -> Phase 3
