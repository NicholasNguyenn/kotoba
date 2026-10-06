"""Build the corpus and push it to Azure AI Search.

Three sources, one index, discriminated by `doc_type`:
  grammar  - the hand-written catalog (the evidence that matters)
  entry    - JMdict common-word entries
  sentence - Tatoeba Japanese-English pairs

The Free search tier allows 50 MB total, and a 1536-dim vector costs 6 KB per
document, so the vectors dominate the budget and the caps below are the real
constraint. After uploading, `report_storage()` prints what the service
actually consumed so the caps can be raised with evidence rather than hope.

Run:  python -m kotoba.ingest --download   (fetch sources, ~31 MB)
      python -m kotoba.ingest             (parse, embed, upload)
"""

from __future__ import annotations

import argparse
import bz2
import csv
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from azure.core.exceptions import ServiceRequestError, ServiceResponseError

from kotoba.azure_clients import embed
from kotoba.config import get_settings
from kotoba.grammar_detect import load_catalog
from kotoba.search_index import create_or_update_index, index_client, search_client

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

# Caps chosen to stay well inside the Free tier's 50 MB. Start conservative;
# report_storage() says how much room is left.
# Measured 2026-10-05. At 1536 dims, 2,914 documents exceeded the Free tier's
# 50 MB outright. At 512 dims the same corpus uses 11.5 MB (~3.9 KB/doc), a
# 4.4x reduction, leaving room for roughly 9,000 more documents.
#
# The switch was made before the eval sets were frozen and before any retrieval
# mode had run, because embedding dimensions change recall@5 -- doing it later
# would have invalidated the comparison.
# A 1536-dim vector serializes to roughly 30 KB of JSON, so a 100-document
# batch is a ~3 MB POST. The Free tier's shared infrastructure resets those
# connections; 25 keeps each request under a megabyte.
UPLOAD_BATCH = 25

MAX_ENTRIES = 1500
MAX_SENTENCES = 1400

JMDICT_RELEASE = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"
TATOEBA = {
    "jpn_sentences.tsv.bz2": "https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences.tsv.bz2",
    "eng_sentences.tsv.bz2": "https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2",
    "jpn-eng_links.tsv.bz2": "https://downloads.tatoeba.org/exports/per_language/jpn/jpn-eng_links.tsv.bz2",
}


def _get(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  have {dest.name}")
        return
    print(f"  fetching {dest.name} ...", flush=True)
    urllib.request.urlretrieve(url, dest)
    print(f"    {dest.stat().st_size:,} bytes")


def download() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(JMDICT_RELEASE) as r:
        release = json.load(r)
    # The version is in the filename and changes with every release, so pick
    # the asset by shape rather than pinning a URL that will rot.
    asset = next(
        a for a in release["assets"]
        if a["name"].startswith("jmdict-eng-common-") and a["name"].endswith(".json.zip")
    )
    print(f"JMdict release {release['tag_name']}")
    _get(asset["browser_download_url"], RAW / "jmdict-eng-common.json.zip")
    for name, url in TATOEBA.items():
        _get(url, RAW / name)


def _tsv(path: Path):
    with bz2.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)


def grammar_docs() -> list[dict]:
    return [
        {
            "id": e.id,
            "doc_type": "grammar",
            "pattern": e.pattern,
            "content_ja": e.pattern,
            "content_en": f"{e.meaning}. {e.explanation}",
            "jlpt_level": e.level,
            "source": e.source,
        }
        for e in load_catalog()
    ]


def entry_docs(limit: int = MAX_ENTRIES) -> list[dict]:
    zpath = RAW / "jmdict-eng-common.json.zip"
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.endswith(".json"))
        data = json.loads(z.read(name).decode("utf-8"))

    # Entries are ordered by JMdict id, which front-loads symbols and
    # loanwords, so the first N is not a representative vocabulary sample.
    # An even stride across all 22k common words is, and is deterministic.
    words = data["words"]
    stride = max(1, len(words) // limit)
    docs = []
    for w in words[::stride][:limit]:
        ja = (w["kanji"][0]["text"] if w["kanji"] else w["kana"][0]["text"]) if (w["kanji"] or w["kana"]) else ""
        if not ja:
            continue
        reading = w["kana"][0]["text"] if w["kana"] else ""
        glosses = [g["text"] for s in w["sense"] for g in s["gloss"] if g.get("lang") == "eng"]
        docs.append({
            "id": f"jmdict-{w['id']}",
            "doc_type": "entry",
            "pattern": ja,
            "content_ja": f"{ja} {reading}".strip(),
            "content_en": "; ".join(glosses[:8]),
            "jlpt_level": None,  # JMdict carries no JLPT level; Phase 6 concern
            "source": "JMdict (EDRDG, CC BY-SA 4.0)",
        })
    return docs


def sentence_docs(limit: int = MAX_SENTENCES) -> list[dict]:
    jpn = {sid: text for sid, _lang, text in _tsv(RAW / "jpn_sentences.tsv.bz2")}
    # A Japanese sentence often links to several English translations. Keeping
    # more than one would repeat the document id and let Azure upsert over
    # itself, so the first translation wins and the id stays unique.
    first: dict[str, str] = {}
    for row in _tsv(RAW / "jpn-eng_links.tsv.bz2"):
        if len(row) < 2 or row[0] not in jpn or row[0] in first:
            continue
        first[row[0]] = row[1]
        if len(first) >= limit:
            break
    pairs = list(first.items())
    wanted = set(first.values())
    # Read English once, keeping only the ids actually linked: the full file is
    # 25 MB and holding all of it would dwarf the data we keep.
    eng = {sid: text for sid, _lang, text in _tsv(RAW / "eng_sentences.tsv.bz2") if sid in wanted}

    return [
        {
            "id": f"tatoeba-{j}",
            "doc_type": "sentence",
            "pattern": None,
            "content_ja": jpn[j],
            "content_en": eng[e],
            "jlpt_level": None,
            "source": "Tatoeba (CC BY 2.0 FR)",
        }
        for j, e in pairs
        if e in eng
    ]


def build() -> list[dict]:
    docs = grammar_docs() + entry_docs() + sentence_docs()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "corpus.jsonl"
    out.write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in docs) + "\n", encoding="utf-8"
    )
    counts = {t: sum(1 for d in docs if d["doc_type"] == t) for t in ("grammar", "entry", "sentence")}
    print(f"built {len(docs)} docs {counts} -> {out}")
    return docs


def _retry(fn, *args, attempts: int = 4):
    """Azure drops long-lived upload connections; a reset is not a real error.

    Both operations are idempotent -- embedding is pure, and upload_documents
    upserts by key -- so retrying a batch cannot duplicate anything.
    """
    for n in range(attempts):
        try:
            return fn(*args)
        except (ServiceResponseError, ServiceRequestError) as exc:
            if n == attempts - 1:
                raise
            wait = 2**n
            print(f"    {type(exc).__name__}, retrying in {wait}s", flush=True)
            time.sleep(wait)


def upload(docs: list[dict], resume: bool = False) -> None:
    create_or_update_index()
    client = search_client()

    if resume:
        have = _retry(lambda: {d["id"] for d in client.search(search_text="*", select=["id"])})
        docs = [d for d in docs if d["id"] not in have]
        print(f"resume: {len(have)} already indexed, {len(docs)} to go")
        if not docs:
            return
    # The embedding API and the Search upload API both cap batches; 100 keeps
    # each request small enough for both.
    for i in range(0, len(docs), UPLOAD_BATCH):
        batch = docs[i : i + UPLOAD_BATCH]
        texts = [f"{d['content_ja']} {d['content_en']}".strip() for d in batch]
        for d, v in zip(batch, _retry(embed, texts)):
            d["embedding"] = v
        _retry(client.upload_documents, batch)
        print(f"  uploaded {i + len(batch)}/{len(docs)}", flush=True)


def report_storage() -> None:
    stats = index_client().get_service_statistics()
    usage = stats["counters"]["storageSize"]
    docs = stats["counters"]["documentCount"]
    print(f"storage: {usage['usage']:,} / {usage.get('quota') or '?'} bytes, {docs['usage']:,} docs")


def run(do_download: bool = False, resume: bool = False) -> None:
    if do_download:
        download()
    upload(build(), resume=resume)
    report_storage()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    p = argparse.ArgumentParser()
    p.add_argument("--download", action="store_true", help="fetch raw sources first (~31 MB)")
    p.add_argument("--build-only", action="store_true", help="parse to JSONL, no Azure calls")
    p.add_argument("--resume", action="store_true", help="skip documents already in the index")
    a = p.parse_args()
    if a.download:
        download()
    if a.build_only:
        build()
        sys.exit(0)
    run(do_download=False, resume=a.resume)
