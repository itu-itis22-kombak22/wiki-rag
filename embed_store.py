"""
Embedding and vector store pipeline.

Loads chunks from SQLite, generates embeddings with sentence-transformers,
and upserts them into a ChromaDB collection with metadata.

Usage:
    python embed_store.py
"""

import sqlite3

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    DB_PATH,
    EMBED_MODEL,
)

BATCH_SIZE = 32


def load_chunks(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, entity, display_name, type, chunk_index, text FROM chunks ORDER BY entity, chunk_index"
    ).fetchall()
    return [
        {
            "id": r[0],
            "entity": r[1],
            "display_name": r[2],
            "type": r[3],
            "chunk_index": r[4],
            "text": r[5],
        }
        for r in rows
    ]


def get_existing_ids(collection: chromadb.Collection) -> set[str]:
    result = collection.get(include=[])
    return set(result["ids"])


def embed_and_store(chunks: list[dict], collection: chromadb.Collection, model: SentenceTransformer) -> int:
    existing_ids = get_existing_ids(collection)
    new_chunks = [c for c in chunks if c["id"] not in existing_ids]

    if not new_chunks:
        return 0

    upserted = 0
    for start in range(0, len(new_chunks), BATCH_SIZE):
        batch = new_chunks[start : start + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=[c["id"] for c in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {
                    "entity": c["entity"],
                    "display_name": c["display_name"],
                    "type": c["type"],
                    "chunk_index": c["chunk_index"],
                }
                for c in batch
            ],
        )
        upserted += len(batch)
        done = min(start + BATCH_SIZE, len(new_chunks))
        print(f"  Embedded {done}/{len(new_chunks)} chunks...", end="\r")

    print()
    return upserted


def main() -> None:
    print(f"Loading model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    print(f"Connecting to SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    chunks = load_chunks(conn)
    conn.close()
    print(f"Loaded {len(chunks)} chunks from SQLite")

    print(f"Connecting to ChromaDB: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    existing = len(get_existing_ids(collection))
    print(f"Existing vectors in collection: {existing}")

    print("Embedding new chunks...")
    inserted = embed_and_store(chunks, collection, model)

    total = collection.count()
    print(f"Done. Inserted {inserted} new vectors. Total in collection: {total}")


if __name__ == "__main__":
    main()
