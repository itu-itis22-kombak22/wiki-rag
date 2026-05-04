# Product Requirements Document
## Wikipedia RAG Assistant — BLG483E Project 3

---

## 1. Overview

**Product Name:** Wikipedia RAG Assistant  
**Version:** 1.0  
**Date:** May 2026  

### Problem Statement

Students, researchers, and curious users need a way to ask natural language questions about famous historical figures and landmark places without relying on internet-connected services. Existing tools (ChatGPT, Google) require external API calls and raise privacy, cost, and availability concerns.

### Solution

A locally-run Retrieval-Augmented Generation (RAG) system that:
1. Ingests Wikipedia articles for a curated set of people and places
2. Splits, embeds, and indexes them locally
3. Answers user questions grounded exclusively in the ingested content
4. Runs entirely on the user's machine with no external API calls

---

## 2. Goals

| Goal | Success Metric |
|---|---|
| Answer factual questions about known entities | Correct answer rate ≥ 80% on test questions |
| Refuse to hallucinate | Returns "I don't know" for out-of-scope queries |
| Run fully offline | No network calls after initial Wikipedia ingest |
| Fast enough for interactive use | Response time < 30s on Apple Silicon |

---

## 3. User Stories

### US-01 — Ask about a person
> As a user, I want to ask "Who was Albert Einstein?" and receive a factual answer sourced from Wikipedia.

**Acceptance Criteria:**
- System returns a coherent paragraph about Einstein
- Answer mentions at least one verifiable fact (theory of relativity, Nobel Prize, etc.)
- Response time < 30 seconds

### US-02 — Ask about a place
> As a user, I want to ask "Where is the Taj Mahal?" and get its location.

**Acceptance Criteria:**
- System correctly identifies India/Agra as the location
- No hallucinated details

### US-03 — Compare two entities
> As a user, I want to compare "Messi vs Ronaldo" and get a structured comparison.

**Acceptance Criteria:**
- System retrieves chunks from both players
- Answer discusses both entities
- No fabricated statistics

### US-04 — Handle unknown entities gracefully
> As a user, I ask "Who is the president of Mars?" and the system declines gracefully.

**Acceptance Criteria:**
- System returns a clear "I don't know" style response
- Does not hallucinate a Mars president

### US-05 — View source context
> As a power user, I want to see which Wikipedia chunks were used to generate the answer.

**Acceptance Criteria:**
- Expandable "Retrieved context" section shows source chunks
- Each chunk shows the source entity name and similarity distance

### US-06 — Reset conversation
> As a user, I want to clear the chat history and start fresh.

**Acceptance Criteria:**
- "Clear conversation" button removes all messages
- System state is fully reset

---

## 4. Functional Requirements

### 4.1 Ingestion
- FR-01: Fetch Wikipedia plain-text for all 40 entities
- FR-02: Clean and normalize raw text (remove markup, extra whitespace)
- FR-03: Split into 500-character overlapping chunks (100-char overlap)
- FR-04: Store chunks in SQLite with entity name, type, and source URL
- FR-05: Ingestion is idempotent (re-running does not duplicate data)

### 4.2 Embedding
- FR-06: Generate embeddings using `all-MiniLM-L6-v2` (sentence-transformers)
- FR-07: Store embeddings in ChromaDB with `type` metadata (person/place)
- FR-08: Embedding step is idempotent

### 4.3 Retrieval
- FR-09: Classify user query as `person`, `place`, or `both`
- FR-10: Apply ChromaDB metadata filter based on query type
- FR-11: Return top-5 most similar chunks by cosine distance

### 4.4 Generation
- FR-12: Build a grounded prompt with retrieved chunks as context
- FR-13: Call Ollama `llama3.2:3b` for answer generation
- FR-14: Return "I don't know" when context is empty or insufficient
- FR-15: Temperature set to 0.1 to minimize hallucination

### 4.5 UI
- FR-16: Chat-style interface with persistent message history
- FR-17: Sidebar with example questions and context toggle
- FR-18: Query type indicator per response (person/place/both)
- FR-19: Clear/reset button

---

## 5. Non-Functional Requirements

| NFR | Requirement |
|---|---|
| Privacy | No data sent to external services after ingestion |
| Portability | Runs on macOS and Linux with Python 3.11+ |
| Reliability | Graceful error messages if Ollama is not running |
| Idempotency | Ingest and embed pipelines safe to re-run |
| Reproducibility | `requirements.txt` pins all dependencies |

---

## 6. Out of Scope

- Real-time Wikipedia updates
- Multi-language support
- User authentication
- Cloud deployment
- Streaming responses (optional extension)

---

## 7. Technical Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM | Ollama · `llama3.2:3b` |
| Embeddings | `sentence-transformers` · `all-MiniLM-L6-v2` |
| Vector Store | ChromaDB (persistent, local) |
| Relational DB | SQLite (stdlib) |
| UI | Streamlit |
| Data Source | Wikipedia API (MediaWiki) |
