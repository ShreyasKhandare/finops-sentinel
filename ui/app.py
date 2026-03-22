"""
FinOps Sentinel - Streamlit UI
Phase 2: Hybrid retrieval + Cohere reranking + stricter prompting
"""

import sys
import os
from pathlib import Path

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

from ingestion.compliance_ingestor import get_chroma_collection
from retrieval.prompt_templates import (
    COMPLIANCE_SYSTEM_PROMPT,
    COMPLIANCE_USER_PROMPT,
    FALLBACK_RESPONSE,
    CONFIDENCE_THRESHOLD,
)
from retrieval.hybrid_retriever import HybridRetrieverWithRerank

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinOps Sentinel",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .result-card {
        background: #F5F8FA;
        border-left: 4px solid #006D77;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── LOAD RESOURCES ONCE ───────────────────────────────────────────────────────
@st.cache_resource
def load_resources():
    collection = get_chroma_collection()
    retriever = HybridRetrieverWithRerank(collection)
    return collection, retriever

collection, retriever = load_resources()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## FinOps Sentinel")
    st.markdown("*AI Compliance Intelligence*")
    st.divider()

    st.markdown("### Corpus Status")
    st.metric("Compliance Chunks", collection.count())
    st.metric("Documents", "PCI-DSS v4.0.1")
    st.metric("Retrieval", "Hybrid + Rerank")
    st.metric("Phase", "2 - Complete")

    st.divider()
    st.markdown("### Settings")
    n_results = st.slider("Results to retrieve", 1, 10, 5)
    show_distance = st.toggle("Show distance scores", value=True)
    show_full_text = st.toggle("Show full chunk text", value=False)

    st.divider()
    st.markdown("### Phase 2 RAGAS Metrics")
    st.markdown("Faithfulness: 1.00")
    st.markdown("Answer Relevancy: 0.88")
    st.markdown("Context Precision: 0.96")
    st.markdown("Context Recall: 0.76")

    st.divider()
    st.markdown("### Sample Queries")
    sample_queries = [
        "What are the password requirements?",
        "How should cardholder data be encrypted?",
        "What are the access control requirements?",
        "What logging and monitoring is required?",
        "What are the vulnerability management requirements?",
    ]
    selected_sample = st.selectbox(
        "Try a sample query",
        [""] + sample_queries,
        index=0,
    )

# ── MAIN AREA ─────────────────────────────────────────────────────────────────
st.title("FinOps Sentinel")
st.caption("Dual-Corpus AI for Financial Compliance and Code Intelligence - Phase 2")
st.divider()

# ── QUERY INPUT ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])

with col1:
    default_query = selected_sample if selected_sample else ""
    query = st.text_input(
        "Query",
        value=default_query,
        placeholder="e.g. What are the encryption requirements for cardholder data?",
        label_visibility="collapsed",
    )

with col2:
    search_btn = st.button("Search", type="primary", use_container_width=True)

# ── RESULTS ───────────────────────────────────────────────────────────────────
if search_btn and query.strip():

    with st.spinner("Searching with hybrid BM25 + vector + reranking..."):
        try:
            results = retriever.search(query, n_results=n_results)
        except Exception as e:
            st.error(f"Retrieval failed: {e}")
            results = []

    if results:

        min_distance = min(r["distance"] for r in results)

        if min_distance > CONFIDENCE_THRESHOLD:
            answer = FALLBACK_RESPONSE
        else:
            context = "\n\n---\n\n".join([
                f"[Source: {r['source']}, Page {r['page']}]\n{r['text']}"
                for r in results[:5]
            ])

            user_prompt = COMPLIANCE_USER_PROMPT.format(
                context=context,
                question=query,
            )

            with st.spinner("Generating answer..."):
                try:
                    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": COMPLIANCE_SYSTEM_PROMPT,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        temperature=0.0,
                        max_tokens=800,
                    )
                    answer = (response.choices[0].message.content or "").strip()
                except Exception as e:
                    st.error(f"Generation failed: {e}")
                    answer = (
                        "The answer could not be generated. "
                        "See retrieved chunks below."
                    )

        st.markdown("### Answer")
        st.markdown(answer)

        st.divider()
        st.markdown("### Retrieved chunks")
        for i, r in enumerate(results, 1):
            dist = ""
            if show_distance and r.get("distance") is not None:
                dist = f" — distance `{float(r['distance']):.4f}`"
            label = f"{i}. {r['source']}, Page {r['page']}{dist}"
            with st.expander(label):
                text = r["text"]
                if not show_full_text and len(text) > 600:
                    text = text[:600] + "…"
                st.text(text)

    else:
        st.info("No matching chunks were retrieved. Try different wording.")

elif search_btn:
    st.warning("Please enter a search query.")