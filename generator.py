"""
Answer generation using a local Ollama LLM.

Builds a grounded prompt from retrieved chunks and calls the Ollama
/api/generate endpoint. Returns "I don't know" when context is empty
or the model clearly cannot answer from the provided context.
"""

import requests

from config import LLM_MODEL, OLLAMA_URL

_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions about famous people and places.
Answer the user's question using ONLY the context provided below.
- If the answer is clearly present in the context, give a concise, well-structured answer.
- If the context does not contain enough information to answer, respond with exactly: "I don't know based on the available information."
- Do NOT make up facts. Do NOT use prior knowledge outside the context.
- You may quote or paraphrase the context.
"""


def build_prompt(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return (
            f"{_SYSTEM_PROMPT}\n\n"
            "Context: [No relevant information found]\n\n"
            f"Question: {query}\n\nAnswer:"
        )

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("display_name", chunk.get("entity", "Unknown"))
        context_parts.append(f"[{i}] (Source: {source})\n{chunk['text']}")

    context = "\n\n".join(context_parts)
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {query}\n\nAnswer:"
    )


def generate(query: str, chunks: list[dict]) -> str:
    """
    Generate an answer grounded in the provided chunks.

    Returns a plain string response.
    """
    if not chunks:
        return "I don't know based on the available information."

    prompt = build_prompt(query, chunks)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,   # low temperature for factual grounding
                    "num_predict": 512,
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return (
            "Error: Cannot connect to Ollama. "
            "Make sure Ollama is running (`ollama serve`) and the model is pulled "
            f"(`ollama pull {LLM_MODEL}`)."
        )
    except requests.exceptions.Timeout:
        return "Error: Ollama response timed out. The model may be loading; please try again."
    except Exception as exc:
        return f"Error generating response: {exc}"
