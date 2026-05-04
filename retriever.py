"""
Query classification and chunk retrieval.

classify_query() uses a rule-based approach:
  1. Match known entity names directly in the query text.
  2. Fall back to keyword signals (where/who/etc.) for ambiguous queries.
  3. Default to searching both types when no signal is found.
"""

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBED_MODEL,
    PEOPLE,
    PLACES,
    TOP_K,
)

# Build lower-case keyword sets once at import time
_PERSON_KEYWORDS = {
    p.replace("_", " ").lower() for p in PEOPLE
} | {
    p.replace("_", " ").split(",")[0].lower() for p in PEOPLE  # "Napoleon Bonaparte" from "Napoleon_Bonaparte,_France"
}

_PLACE_KEYWORDS = {
    p.replace("_", " ").lower() for p in PLACES
} | {
    p.replace("_", " ").split(",")[0].lower() for p in PLACES
}

# Signals that hint at a query type
_PLACE_SIGNALS = {"where", "located", "location", "built", "visit", "country", "city", "stand", "stands", "found"}
_PERSON_SIGNALS = {"who", "born", "career", "invented", "discover", "wrote", "played", "won", "known for", "famous for"}


def classify_query(query: str) -> str:
    """
    Return 'person', 'place', or 'both'.

    Priority:
      1. Exact entity name match → unambiguous
      2. Both types matched → 'both'
      3. Keyword signal bias
      4. Default → 'both'
    """
    q = query.lower()

    has_person = any(kw in q for kw in _PERSON_KEYWORDS)
    has_place = any(kw in q for kw in _PLACE_KEYWORDS)

    if has_person and has_place:
        return "both"
    if has_person:
        return "person"
    if has_place:
        return "place"

    # Keyword signal fallback
    words = set(q.split())
    if _PLACE_SIGNALS & words:
        return "place"
    if _PERSON_SIGNALS & words:
        return "person"

    return "both"


# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------

_model: SentenceTransformer | None = None
_collection: chromadb.Collection | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_collection(name=COLLECTION_NAME)
    return _collection


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, query_type: str | None = None, top_k: int = TOP_K) -> list[dict]:
    """
    Embed the query and search ChromaDB.

    Args:
        query:      User question.
        query_type: 'person', 'place', or 'both'. Auto-detected if None.
        top_k:      Number of chunks to return.

    Returns:
        List of dicts with keys: text, entity, display_name, type, chunk_index, distance.
    """
    if query_type is None:
        query_type = classify_query(query)

    model = _get_model()
    collection = _get_collection()

    embedding = model.encode(query).tolist()

    where_filter: dict | None = None
    if query_type == "person":
        where_filter = {"type": "person"}
    elif query_type == "place":
        where_filter = {"type": "place"}
    # "both" → no filter

    kwargs: dict = {
        "query_embeddings": [embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append(
            {
                "text": doc,
                "entity": meta["entity"],
                "display_name": meta["display_name"],
                "type": meta["type"],
                "chunk_index": meta["chunk_index"],
                "distance": round(dist, 4),
            }
        )
    return chunks
