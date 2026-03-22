"""
FinOps Sentinel — Streamlit UI
Phase 1: Basic compliance corpus query interface
"""

import sys
from pathlib import Path

import streamlit as st

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ingestion.compliance_ingestor import get_chroma_collection, query_compliance

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinOps Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B2A4A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .result-card {
        background: #F5F8FA;
        border-left: 4px solid #006D77;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .metric-chip {
        background: #E8F5E9;
        color: #1E7E34;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .source-chip {
        background: #EBF4F7;
        color: #006D77;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.markdown("## FinOps Sentinel")
    st.markdown("*AI Compliance Intelligence*")
    st.divider()

    st.markdown("### Corpus Status")
    collection = get_chroma_collection()
    chunk_count = collection.count()

    st.metric("Compliance Chunks", chunk_count)
    st.metric("Documents", "PCI-DSS v4.0.1")
    st.metric("Embedding Model", "all-MiniLM-L6-v2")

    st.divider()

    st.markdown("### Settings")
    n_results = st.slider("Results to retrieve", 1, 10, 5)
    show_distance = st.toggle("Show distance scores", value=True)
    show_full_text = st.toggle("Show full chunk text", value=False)

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
st.markdown('<div class="main-header">🛡️ FinOps Sentinel</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Dual-Corpus AI for Financial Compliance & Code Intelligence — Phase 1</div>', unsafe_allow_html=True)

# ── QUERY INPUT ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])

with col1:
    # Use sample query if selected, otherwise use text input
    default_query = selected_sample if selected_sample else ""
    query = st.text_input(
        "Ask a compliance question",
        value=default_query,
        placeholder="e.g. What are the encryption requirements for cardholder data?",
        label_visibility="collapsed",
    )

with col2:
    search_btn = st.button("Search", type="primary", use_container_width=True)

# ── RESULTS ───────────────────────────────────────────────────────────────────
# ── RESULTS ───────────────────────────────────────────────────────────────────
if search_btn and query.strip():

    with st.spinner("Searching compliance corpus..."):
        try:
            results = query_compliance(query, collection, n_results=n_results)
        except Exception as e:
            st.error(f"Retrieval failed: {e}")
            results = []

    if results:
        # ── LLM ANSWER GENERATION ─────────────────────────────────────────
        from openai import OpenAI
        from dotenv import load_dotenv
        import os
        load_dotenv()

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Build context from top chunks
        context = "\n\n---\n\n".join([
            f"[Source: {r['source']}, Page {r['page']}]\n{r['text']}"
            for r in results[:5]
        ])

        system_prompt = """You are a financial compliance expert assistant.
Answer questions based ONLY on the provided regulatory document context.
Always cite the specific page numbers your answer comes from.
If the answer is not in the provided context, say exactly:
'I cannot find this information in the provided compliance documents.'
Be precise and concise. Use bullet points for multiple requirements."""

        user_prompt = f"""Context from compliance documents:
{context}

Question: {query}

Provide a clear, structured answer with page citations."""

        with st.spinner("Generating answer..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=600,
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"LLM generation failed: {e}"

        # ── DISPLAY ANSWER ─────────────────────────────────────────────────
        st.markdown(f"### Answer")
        st.markdown(f"""
        <div style="background:#F0F7FF; border-left:4px solid #1B2A4A;
        padding:1.2rem; border-radius:0 8px 8px 0; margin-bottom:1.5rem;">
        {answer}
        </div>
        """, unsafe_allow_html=True)

        # ── RETRIEVED CHUNKS ───────────────────────────────────────────────
        with st.expander(f"View {len(results)} retrieved source chunks", expanded=False):
            for i, result in enumerate(results):
                col_rank, col_source, col_page, col_dist = st.columns([0.5, 2, 1, 1])
                with col_rank:
                    st.markdown(f"**#{i+1}**")
                with col_source:
                    st.markdown(f"📄 `{result['source']}`")
                with col_page:
                    st.markdown(f"Page **{result['page']}**")
                with col_dist:
                    if show_distance:
                        score = result['distance']
                        color = "green" if score < 0.5 else "orange" if score < 0.8 else "red"
                        st.markdown(f":{color}[{score:.4f}]")

                text = result['text']
                if not show_full_text:
                    text = text[:400] + "..." if len(text) > 400 else text
                st.markdown(f"""
                <div class="result-card">{text}</div>
                """, unsafe_allow_html=True)
                st.divider()

    else:
        st.warning("No results found. Try a different query.")

elif search_btn and not query.strip():
    st.warning("Please enter a query first.")

else:
    st.markdown("### How to use FinOps Sentinel")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Step 1**\nType a compliance question above")
    with col2:
        st.info("**Step 2**\nClick Search to query PCI-DSS corpus")
    with col3:
        st.info("**Step 3**\nGet AI answer with page citations")

    st.divider()
    st.markdown("#### Currently indexed documents")
    st.markdown("- 📋 **PCI-DSS v4.0.1** — 413 chunks")
# ── FOOTER ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#6B7280; font-size:0.8rem;'>"
    "FinOps Sentinel Phase 1 · Compliance Corpus · Built with LangChain + ChromaDB + Streamlit"
    "</div>",
    unsafe_allow_html=True,
)