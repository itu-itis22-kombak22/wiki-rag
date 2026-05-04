# Production Deployment Recommendations
## Wikipedia RAG Assistant

---

## Current State vs Production

The current system is a **local prototype** designed to run on a single developer laptop. Moving to production requires addressing scalability, reliability, observability, and security.

---

## 1. Infrastructure

### Containerization
Package all components into Docker containers:

```dockerfile
# Example: Ollama + app in docker-compose
services:
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports: ["11434:11434"]

  app:
    build: .
    ports: ["8501:8501"]
    depends_on: [ollama]
    volumes:
      - ./data:/app/data
```

This eliminates "works on my machine" issues and simplifies instructor setup.

### Cloud Deployment Options

| Option | Pros | Cons |
|---|---|---|
| AWS EC2 (g4dn.xlarge) | GPU acceleration, managed infra | Cost ($0.50/hr+) |
| Hugging Face Spaces | Free tier, easy Streamlit deploy | No GPU on free tier, limited RAM |
| Self-hosted VPS | Full control, cheapest | Manual ops, no auto-scaling |
| Modal / Replicate | Serverless GPU, pay-per-use | Vendor lock-in |

**Recommendation:** For a university project demo, **Hugging Face Spaces** (CPU tier) is simplest. For a real product, **AWS EC2 g4dn.xlarge** with GPU inference.

---

## 2. Model Upgrades

### LLM
| Swap | Impact |
|---|---|
| `llama3.2:3b` → `llama3.1:8b` | Better reasoning, slower on CPU |
| `llama3.2:3b` → `mistral:7b` | Better instruction following |
| Any local → `claude-3-5-haiku` via API | Best quality, breaks offline constraint |

For production with a GPU: `llama3.1:8b` is the sweet spot for quality vs cost.

### Embeddings
| Swap | Impact |
|---|---|
| `all-MiniLM-L6-v2` → `nomic-embed-text` | Larger (768-dim), better semantic search |
| `all-MiniLM-L6-v2` → `BAAI/bge-large-en-v1.5` | State-of-the-art retrieval |

---

## 3. Vector Store

ChromaDB is suitable for prototypes but has limitations at scale.

| Scale | Recommendation |
|---|---|
| < 100k chunks | ChromaDB (current) |
| 100k – 10M chunks | **pgvector** (PostgreSQL extension) |
| > 10M chunks | **Weaviate** or **Qdrant** (dedicated vector DB) |

**pgvector** is the best production choice because:
- Runs alongside your existing relational data
- ACID guarantees
- Familiar SQL interface
- Scales with standard Postgres tooling (replication, backups)

Migration path: replace `chromadb` client calls in `embed_store.py` and `retriever.py` with `psycopg2` + `pgvector` extension.

---

## 4. Retrieval Quality Improvements

### Hybrid Search (BM25 + Dense)
Combine keyword search (BM25 via SQLite FTS5) with vector search and merge results with Reciprocal Rank Fusion:

```python
# Conceptual: merge dense + sparse scores
dense_results = chroma_collection.query(...)
sparse_results = sqlite_fts.search(query)
final = reciprocal_rank_fusion(dense_results, sparse_results)
```

This dramatically improves recall for named-entity queries ("What year was the Eiffel Tower built?").

### Re-ranking
Add a cross-encoder re-ranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) after initial retrieval to re-score the top-10 candidates and return only the best 5.

### Chunking
Replace fixed-size chunking with **semantic chunking** (split at topic boundaries detected by embedding similarity drops) for better chunk coherence.

---

## 5. Observability

Add structured logging and latency tracking:

```python
import time, logging

start = time.perf_counter()
chunks = retrieve(query, query_type)
answer = generate(query, chunks)
elapsed = time.perf_counter() - start

logging.info({
    "query": query,
    "query_type": query_type,
    "chunks_retrieved": len(chunks),
    "latency_s": round(elapsed, 2),
})
```

Ship logs to **Grafana + Loki** or **Datadog** in production.

---

## 6. Caching

Cache embeddings and LLM responses for repeated queries:

```python
import hashlib, json
from functools import lru_cache

@lru_cache(maxsize=256)
def cached_retrieve(query_hash: str, query_type: str):
    ...
```

For production: **Redis** with TTL-based cache invalidation.

---

## 7. Data Freshness

Wikipedia articles change. Production options:

| Approach | Complexity | Freshness |
|---|---|---|
| Manual re-ingest | Low | Stale |
| Scheduled weekly re-ingest (cron) | Medium | Weekly |
| Wikipedia change feed (EventStreams API) | High | Near real-time |

**Recommendation:** Scheduled weekly re-ingest with incremental upsert (idempotent pipeline already implemented).

---

## 8. Security

- Serve Streamlit behind **nginx reverse proxy** with HTTPS
- Rate-limit the `/api/generate` Ollama endpoint (not exposed publicly)
- If expanding entity list from user input: **sanitize Wikipedia titles** to prevent SSRF

---

## Summary

| Priority | Action |
|---|---|
| High | Containerize with Docker Compose |
| High | Switch vector store to pgvector for scale |
| Medium | Add hybrid BM25 + dense retrieval |
| Medium | Upgrade to `llama3.1:8b` on GPU server |
| Medium | Add structured logging and latency metrics |
| Low | Implement Redis caching for repeated queries |
| Low | Weekly Wikipedia re-ingest cron job |
