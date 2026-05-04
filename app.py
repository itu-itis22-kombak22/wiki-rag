"""
Streamlit chat interface for the Local Wikipedia RAG Assistant.

Usage:
    streamlit run app.py
"""

import streamlit as st

from generator import generate
from retriever import classify_query, retrieve

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Wikipedia RAG Assistant",
    page_icon="📚",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_context" not in st.session_state:
    st.session_state.show_context = False

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📚 Wikipedia RAG")
    st.caption("Local RAG · llama3.2:3b · all-MiniLM-L6-v2")

    st.divider()

    st.session_state.show_context = st.toggle(
        "Show retrieved context", value=st.session_state.show_context
    )

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Example questions")

    example_questions = [
        "Who was Albert Einstein and what is he known for?",
        "What did Marie Curie discover?",
        "Why is Nikola Tesla famous?",
        "Where is the Eiffel Tower located?",
        "What was the Colosseum used for?",
        "Compare Lionel Messi and Cristiano Ronaldo",
        "Which famous place is located in Turkey?",
        "Compare Albert Einstein and Nikola Tesla",
        "Who is the president of Mars?",
    ]

    for q in example_questions:
        if st.button(q, use_container_width=True, key=f"ex_{q[:20]}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

st.title("Wikipedia RAG Assistant")
st.caption("Ask me about famous people and places. All answers come from local Wikipedia data.")

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and st.session_state.show_context and msg.get("chunks"):
            with st.expander("📄 Retrieved context", expanded=False):
                for i, chunk in enumerate(msg["chunks"], 1):
                    st.markdown(
                        f"**[{i}] {chunk['display_name']}** "
                        f"*(type: {chunk['type']}, distance: {chunk['distance']})*"
                    )
                    st.text(chunk["text"][:400] + ("..." if len(chunk["text"]) > 400 else ""))
                    st.divider()

# Process the last user message if it hasn't been answered yet
last_messages = st.session_state.messages
if last_messages and last_messages[-1]["role"] == "user":
    user_query = last_messages[-1]["content"]

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            query_type = classify_query(user_query)
            chunks = retrieve(user_query, query_type)
            answer = generate(user_query, chunks)

        # Query type badge
        type_colors = {"person": "🟢", "place": "🔵", "both": "🟡"}
        badge = type_colors.get(query_type, "⚪")
        st.caption(f"{badge} Query type detected: **{query_type}**")

        st.markdown(answer)

        if st.session_state.show_context and chunks:
            with st.expander("📄 Retrieved context", expanded=False):
                for i, chunk in enumerate(chunks, 1):
                    st.markdown(
                        f"**[{i}] {chunk['display_name']}** "
                        f"*(type: {chunk['type']}, distance: {chunk['distance']})*"
                    )
                    st.text(chunk["text"][:400] + ("..." if len(chunk["text"]) > 400 else ""))
                    st.divider()

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "chunks": chunks,
            "query_type": query_type,
        }
    )

# Chat input
if prompt := st.chat_input("Ask about a famous person or place..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
