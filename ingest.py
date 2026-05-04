"""
Wikipedia ingestion pipeline.

Fetches plain-text extracts from Wikipedia for all configured people and places,
splits them into overlapping chunks, and stores everything in SQLite.

Usage:
    python ingest.py
"""

import re
import sqlite3
import time

import requests

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DB_PATH,
    PEOPLE,
    PLACES,
    WIKI_API_URL,
)


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": "WikiRAG/1.0 (BLG483E course project; https://github.com/itu-itis22-kombak22/wiki-rag) python-requests"
}


def fetch_wikipedia(title: str) -> tuple[str, str]:
    """Return (plain_text, page_url) for the given Wikipedia page title."""
    params = {
        "action": "query",
        "prop": "extracts|info",
        "explaintext": "1",
        "inprop": "url",
        "titles": title,
        "format": "json",
        "redirects": "1",
    }
    resp = requests.get(WIKI_API_URL, params=params, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    pages = data["query"]["pages"]
    page = next(iter(pages.values()))

    if "missing" in page:
        raise ValueError(f"Wikipedia page not found: {title}")

    text = page.get("extract", "")
    url = page.get("fullurl", f"https://en.wikipedia.org/wiki/{title}")
    return text, url


# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalize whitespace and remove Wikipedia boilerplate noise."""
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove lines that are pure section headers (== Header ==)
    text = re.sub(r"^=+[^=]+=+\s*$", "", text, flags=re.MULTILINE)
    # Collapse runs of spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping fixed-size chunks.

    Splits at sentence boundaries ('. ') when possible so chunks start cleanly.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= size:
            current = (current + " " + sentence).strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            # Start new chunk with overlap from end of previous chunk
            if chunks:
                overlap_text = chunks[-1][-overlap:] if len(chunks[-1]) > overlap else chunks[-1]
                current = (overlap_text + " " + sentence).strip()
            else:
                current = sentence

            # If a single sentence is longer than chunk size, force-split it
            while len(current) > size:
                chunks.append(current[:size])
                current = current[size - overlap:]

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c.strip()) > 20]


# ---------------------------------------------------------------------------
# SQLite storage
# ---------------------------------------------------------------------------

def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id           TEXT PRIMARY KEY,
            entity       TEXT NOT NULL,
            display_name TEXT NOT NULL,
            type         TEXT NOT NULL CHECK(type IN ('person', 'place')),
            chunk_index  INTEGER NOT NULL,
            text         TEXT NOT NULL,
            source_url   TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entity ON chunks(entity)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_type   ON chunks(type)")
    conn.commit()


def store_chunks(
    conn: sqlite3.Connection,
    entity: str,
    display_name: str,
    entity_type: str,
    chunks: list[str],
    source_url: str,
) -> int:
    """Insert chunks; skip if already present. Returns number inserted."""
    inserted = 0
    for i, text in enumerate(chunks):
        chunk_id = f"{entity}__{i}"
        existing = conn.execute(
            "SELECT 1 FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO chunks (id, entity, display_name, type, chunk_index, text, source_url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chunk_id, entity, display_name, entity_type, i, text, source_url),
            )
            inserted += 1
    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Main ingestion loop
# ---------------------------------------------------------------------------

def ingest_entity(
    conn: sqlite3.Connection,
    title: str,
    display_name: str,
    entity_type: str,
) -> dict:
    result = {"entity": display_name, "type": entity_type, "status": "ok", "chunks": 0}
    try:
        text, url = fetch_wikipedia(title)
        text = clean_text(text)
        if not text:
            result["status"] = "empty"
            return result
        chunks = chunk_text(text)
        inserted = store_chunks(conn, title, display_name, entity_type, chunks, url)
        result["chunks"] = inserted
        total = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE entity = ?", (title,)
        ).fetchone()[0]
        result["total_chunks"] = total
    except Exception as exc:
        result["status"] = f"error: {exc}"
    return result


def main() -> None:
    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    entities: list[tuple[str, str, str]] = []
    for title in PEOPLE:
        display = title.replace("_", " ").replace(",_", ", ")
        entities.append((title, display, "person"))
    for title in PLACES:
        display = title.replace("_", " ").replace(",_", ", ")
        entities.append((title, display, "place"))

    total = len(entities)
    print(f"Ingesting {total} entities...\n")

    for idx, (title, display, etype) in enumerate(entities, 1):
        print(f"[{idx:2d}/{total}] {display} ({etype})... ", end="", flush=True)
        result = ingest_entity(conn, title, display, etype)
        if result["status"] == "ok":
            new = result["chunks"]
            tot = result.get("total_chunks", new)
            print(f"OK — {new} new chunks ({tot} total)")
        else:
            print(f"SKIP — {result['status']}")
        time.sleep(0.3)  # be polite to Wikipedia

    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"\nDone. Total chunks in database: {total_chunks}")
    conn.close()


if __name__ == "__main__":
    main()
