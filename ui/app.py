"""
FinOps Sentinel - Streamlit UI
Phase 3: LangGraph multi-agent system
"""

import sys
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent))

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinOps Sentinel",
    page_icon="🛡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── LOAD RESOURCES ONCE ───────────────────────────────────────────────────────
@st.cache_resource
def load_resources():
    """Load corpus, auto-ingest if empty, build retriever, compile graph."""
    from ingestion.compliance_ingestor import get_chroma_collection, ingest_pdf
    from retrieval.hybrid_retriever import HybridRetrieverWithRerank
    from agents.graph import get_graph

    # Load collection
    collection = get_chroma_collection()

    # Auto-ingest if corpus is empty (first deploy on Streamlit Cloud)
    if collection.count() == 0:
        pdf_dir = Path("evaluation/test_datasets")
        pdfs = list(pdf_dir.glob("*.pdf"))
        if pdfs:
            for pdf in pdfs:
                ingest_pdf(pdf, collection)

    # Build retriever
    retriever = HybridRetrieverWithRerank(collection)

    # Compile agent graph
    graph = get_graph()

    return collection, retriever, graph

collection, retriever, graph = load_resources()

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## FinOps Sentinel")
    st.markdown("*AI Compliance Intelligence*")
    st.divider()

    st.markdown("### System Status")
    st.success("LangGraph Agent: Active")
    st.metric("Corpus", "PCI-DSS v4.0.1")
    st.metric("Chunks", collection.count())
    st.metric("Retrieval", "Hybrid + Rerank")
    st.metric("Phase", "3 - Multi-Agent")

    st.divider()
    st.markdown("### Agent Pipeline")
    st.markdown("1. QueryClassifier")
    st.markdown("2. ComplianceMapper")
    st.markdown("3. FormatResponse")

    st.divider()
    st.markdown("### Phase 2 RAGAS Scores")
    st.markdown("Faithfulness: **1.00** ✅")
    st.markdown("Answer Relevancy: **0.88** ✅")
    st.markdown("Context Precision: **0.96** ✅")
    st.markdown("Context Recall: **0.76** ✅")

    st.divider()
    st.markdown("### Sample Queries")
    sample_queries = [
        "What are the password requirements?",
        "How should cardholder data be encrypted?",
        "What are the access control requirements?",
        "What logging and monitoring is required?",
        "What are the vulnerability management requirements?",
        "What does PCI-DSS say about network security?",
    ]
    selected_sample = st.selectbox(
        "Try a sample",
        [""] + sample_queries,
        index=0,
    )

# ── MAIN AREA ─────────────────────────────────────────────────────────────────
st.title("FinOps Sentinel")
st.caption("Dual-Corpus AI for Financial Compliance and Code Intelligence - Phase 3")
st.divider()

# ── QUERY INPUT ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])

with col1:
    default_query = selected_sample if selected_sample else ""
    query = st.text_input(
        "Query",
        value=default_query,
        placeholder="e.g. What are the PCI-DSS requirements for cardholder data encryption?",
        label_visibility="collapsed",
    )

with col2:
    search_btn = st.button("Search", type="primary", use_container_width=True)

# ── RESULTS ───────────────────────────────────────────────────────────────────
if search_btn and query.strip():

    with st.spinner("Running agent pipeline... (first query may take 60 seconds while corpus loads)"):
        try:
            result = graph.invoke({"query": query})
        except Exception as e:
            st.error(f"Agent pipeline failed: {e}")
            result = None

    if result:

        # Routing info
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            corpus = result.get("corpus", "unknown").upper()
            color = (
                "green" if corpus == "COMPLIANCE"
                else "blue" if corpus == "CODE"
                else "orange"
            )
            st.markdown(f"**Routed to:** :{color}[{corpus}]")
        with col_r2:
            confidence = result.get("confidence", 0)
            st.markdown(f"**Confidence:** {confidence:.0%}")
        with col_r3:
            st.markdown("**Agents run:** QueryClassifier + ComplianceMapper")

        with st.expander("Routing decision"):
            st.caption(result.get("routing_reason", ""))

        st.divider()

        # Final answer
        st.markdown("### Answer")
        answer = result.get("final_answer", "No answer generated.")
        st.info(answer)

        # Source chunks
        compliance_results = result.get("compliance_results", [])
        if compliance_results:
            with st.expander(f"View {len(compliance_results)} source chunks"):
                for i, r in enumerate(compliance_results):
                    c1, c2, c3 = st.columns([0.5, 2, 1])
                    with c1:
                        st.markdown(f"**#{i+1}**")
                    with c2:
                        st.markdown(f"`{r.get('source', 'unknown')}`")
                    with c3:
                        st.markdown(f"Page **{r.get('page', '?')}**")
                    st.caption(r.get("text", "")[:300] + "...")
                    st.divider()

else:
    if search_btn:
        st.warning("Please enter a query first.")
    else:
        st.markdown("### How to use FinOps Sentinel")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("Step 1: Type a compliance question")
        with c2:
            st.info("Step 2: LangGraph agent classifies and routes")
        with c3:
            st.info("Step 3: Hybrid retrieval + LLM analysis")

        st.divider()
        st.markdown("**Phase 3:** LangGraph multi-agent orchestration")
        st.markdown("**Corpus:** PCI-DSS v4.0.1")
        st.markdown("**Pipeline:** QueryClassifier -> ComplianceMapper -> FormatResponse")

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("FinOps Sentinel Phase 3 - LangGraph Multi-Agent - RAGAS Faithfulness 1.0")