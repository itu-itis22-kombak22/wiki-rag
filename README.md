# Wikipedia RAG Assistant

A local, ChatGPT-style question-answering system about famous people and places — running entirely on your laptop. No external APIs are used.

## Architecture Overview

```
Wikipedia API
     │
     ▼
ingest.py ──► SQLite (chunks table)
                    │
                    ▼
            embed_store.py ──► ChromaDB (vectors + metadata)
                                      │
                    ┌─────────────────┘
                    ▼
              retriever.py (query classification + similarity search)
                    │
                    ▼
              generator.py (Ollama llama3.2:3b prompt + generate)
                    │
                    ▼
                app.py (Streamlit chat UI)
```

### Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Vector store | **Option B**: single ChromaDB collection + `type` metadata | Enables mixed queries (people + places) in one search call |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` | Fully local, fast, no Ollama dependency for embeddings |
| LLM | `llama3.2:3b` via Ollama | Lightweight, runs on CPU/Apple Silicon without GPU |
| Chunking | 500-char fixed-size with 100-char overlap | Balances context richness vs retrieval precision |
| Query routing | Keyword/entity-name matching (rule-based) | Simple, fast, no LLM call needed for routing |

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com) installed and running

---

## Setup

### 1. Clone and enter the project

```bash
git clone <repo-url> wiki-rag
cd wiki-rag
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Pull the local LLM model

```bash
ollama pull llama3.2:3b
```

Make sure Ollama is running:

```bash
ollama serve   # keep this terminal open
```

---

## Running the System

### Step 1 — Ingest Wikipedia data

Fetches pages for 20 people and 20 places and stores chunks in SQLite.

```bash
python ingest.py
```

Expected output:
```
Ingesting 40 entities...
[ 1/40] Albert Einstein (person)... OK — 42 new chunks (42 total)
...
Done. Total chunks in database: 1823
```

### Step 2 — Generate embeddings

Embeds all chunks and stores them in ChromaDB.

```bash
python embed_store.py
```

Expected output:
```
Loading model: all-MiniLM-L6-v2
Loaded 1823 chunks from SQLite
Embedding new chunks...
  Embedded 1823/1823 chunks...
Done. Inserted 1823 new vectors. Total in collection: 1823
```

Both steps are **idempotent** — safe to run again without duplicating data.

### Step 3 — Start the chat interface

```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## Example Queries

### People
- Who was Albert Einstein and what is he known for?
- What did Marie Curie discover?
- Why is Nikola Tesla famous?
- Compare Lionel Messi and Cristiano Ronaldo

### Places
- Where is the Eiffel Tower located?
- Why is the Great Wall of China important?
- What was the Colosseum used for?
- Where is Mount Everest?

### Mixed
- Which famous place is located in Turkey?
- Which person is associated with electricity?
- Compare Albert Einstein and Nikola Tesla
- Compare the Eiffel Tower and the Statue of Liberty

### Failure cases (expected "I don't know")
- Who is the president of Mars?
- Tell me about John Doe

---

## Project Structure

```
wiki-rag/
├── config.py          # Entity lists, model names, storage paths
├── ingest.py          # Wikipedia fetch + clean + chunk + SQLite
├── embed_store.py     # Sentence-transformers embeddings + ChromaDB
├── retriever.py       # Query type classification + vector search
├── generator.py       # Ollama LLM prompt building + generation
├── app.py             # Streamlit chat UI
├── requirements.txt
├── README.md
├── product_prd.md     # Product requirements document
├── recommendation.md  # Production deployment recommendations
└── data/
    ├── wiki.db        # SQLite (created by ingest.py)
    └── chroma_db/     # ChromaDB (created by embed_store.py)
```

---

## Entities Covered

### People (20)
Albert Einstein, Marie Curie, Leonardo da Vinci, William Shakespeare, Ada Lovelace, Nikola Tesla, Lionel Messi, Cristiano Ronaldo, Taylor Swift, Frida Kahlo, Isaac Newton, Stephen Hawking, Elon Musk, Cleopatra, Napoleon Bonaparte, Mahatma Gandhi, Nelson Mandela, Galileo Galilei, Charles Darwin, Wolfgang Amadeus Mozart

### Places (20)
Eiffel Tower, Great Wall of China, Taj Mahal, Grand Canyon, Machu Picchu, Colosseum, Hagia Sophia, Statue of Liberty, Pyramids of Giza, Mount Everest, Stonehenge, Angkor Wat, Chichen Itza, Petra, Acropolis of Athens, Niagara Falls, Amazon River, Sahara, Victoria Falls, Galápagos Islands
