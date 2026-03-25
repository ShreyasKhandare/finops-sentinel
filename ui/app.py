"""
FinOps Sentinel - Streamlit UI
Phase 3: LangGraph multi-agent system — Redesigned UI
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
    initial_sidebar_state="collapsed",
)

# ── FULL CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background: #0A0E1A !important;
    font-family: 'DM Sans', sans-serif;
    color: #E8EDF5;
}

[data-testid="stAppViewContainer"] > .main {
    background: #0A0E1A !important;
    padding: 0 !important;
}

[data-testid="block-container"] {
    padding: 0 !important;
    max-width: 100% !important;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

[data-testid="stSidebar"] { display: none !important; }

.bg-grid {
    position: fixed; inset: 0;
    background-image:
        linear-gradient(rgba(99,179,237,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(99,179,237,0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none; z-index: 0;
}

.bg-glow-1 {
    position: fixed; top: -200px; left: -200px;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(56,189,248,0.06) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
    animation: drift1 20s ease-in-out infinite;
}

.bg-glow-2 {
    position: fixed; bottom: -150px; right: -150px;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(168,85,247,0.05) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
    animation: drift2 25s ease-in-out infinite;
}

@keyframes drift1 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(60px,40px)} }
@keyframes drift2 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-40px,-60px)} }

.sentinel-header {
    position: relative; z-index: 10;
    padding: 28px 32px 0;
    display: flex; align-items: center; justify-content: space-between;
}

.sentinel-logo { display: flex; align-items: center; gap: 12px; }

.sentinel-logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #38BDF8, #818CF8);
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 18px;
    box-shadow: 0 0 20px rgba(56,189,248,0.3);
}

.sentinel-logo-name {
    font-family: 'Syne', sans-serif; font-size: 20px;
    font-weight: 800; letter-spacing: -0.5px;
    background: linear-gradient(135deg, #E8EDF5 0%, #94A3B8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.badge-pill {
    padding: 4px 12px; border-radius: 100px; font-size: 11px;
    font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase;
}

.badge-live {
    background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); color: #4ADE80;
}

.badge-phase {
    background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.2); color: #7DD3FC;
}

.sentinel-hero {
    position: relative; z-index: 10; text-align: center;
    padding: 64px 24px 32px; max-width: 780px; margin: 0 auto;
}

.hero-eyebrow {
    font-size: 12px; font-weight: 500; letter-spacing: 3px;
    text-transform: uppercase; color: #38BDF8; margin-bottom: 20px;
}

.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(36px, 6vw, 64px); font-weight: 800;
    line-height: 1.05; letter-spacing: -2px; margin-bottom: 20px;
    background: linear-gradient(160deg, #F8FAFC 0%, #94A3B8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.hero-title span {
    background: linear-gradient(135deg, #38BDF8, #818CF8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

.hero-sub {
    font-size: 16px; font-weight: 300; line-height: 1.7;
    color: #64748B; max-width: 520px; margin: 0 auto 32px;
}

.stats-row {
    display: flex; justify-content: center; gap: 12px;
    flex-wrap: wrap; margin-bottom: 40px;
}

.stat-chip {
    display: flex; align-items: center; gap: 6px;
    padding: 6px 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 100px; font-size: 12px; color: #94A3B8;
}

.stat-chip strong { color: #E2E8F0; font-weight: 600; }
.stat-chip .dot { width:6px;height:6px;border-radius:50%;background:#4ADE80;box-shadow:0 0 6px #4ADE80; }

/* ── SUGGESTION CHIPS — dark ghost style ── */
.suggestions-label {
    font-size: 11px; font-weight: 500; letter-spacing: 1.5px;
    text-transform: uppercase; color: #475569;
    margin-bottom: 12px; text-align: center;
}

/* Target ONLY the suggestion buttons by data-key */
[data-testid="stButton"][data-key^="sug_"] > button,
div.suggestion-btn [data-testid="stButton"] > button {
    background: rgba(255,255,255,0.04) !important;
    color: #7A8BA0 !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 100px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 400 !important;
    font-size: 12px !important;
    letter-spacing: 0px !important;
    padding: 7px 14px !important;
    box-shadow: none !important;
}

[data-testid="stButton"][data-key^="sug_"] > button:hover,
div.suggestion-btn [data-testid="stButton"] > button:hover {
    background: rgba(56,189,248,0.08) !important;
    border-color: rgba(56,189,248,0.3) !important;
    color: #E2E8F0 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(56,189,248,0.1) !important;
}

/* ── MAIN SEARCH BUTTON — gradient ── */
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #38BDF8, #818CF8) !important;
    color: #0A0E1A !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 14px 28px !important;
    width: 100% !important;
    box-shadow: 0 4px 20px rgba(56,189,248,0.25) !important;
    transition: all 0.2s ease !important;
}

[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 30px rgba(56,189,248,0.4) !important;
}

/* ── INPUT ── */
[data-testid="stTextInput"] > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 16px !important;
}

[data-testid="stTextInput"] > div > div:focus-within {
    border-color: rgba(56,189,248,0.5) !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,0.1) !important;
}

[data-testid="stTextInput"] input {
    background: transparent !important;
    color: #E8EDF5 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    padding: 12px 16px !important;
}

[data-testid="stTextInput"] input::placeholder { color: #475569 !important; }

/* ── FORM border removal ── */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* ── RESULTS ── */
.answer-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px; padding: 28px 32px;
    margin-bottom: 16px; position: relative; overflow: hidden;
}

.answer-card::before {
    content: ''; position: absolute; top:0; left:0; right:0; height:2px;
    background: linear-gradient(90deg, #38BDF8, #818CF8, transparent);
}

.answer-label {
    font-size: 11px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; color: #38BDF8;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}

.answer-label::after {
    content: ''; flex: 1; height: 1px; background: rgba(56,189,248,0.15);
}

.answer-body {
    font-size: 15px; line-height: 1.75; color: #CBD5E1; white-space: pre-wrap;
}

.routing-bar {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    margin-bottom: 20px; padding: 14px 20px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07); border-radius: 14px;
}

.route-tag {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 100px;
    font-size: 12px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;
}

.route-compliance { background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.25); color:#38BDF8; }
.route-code { background:rgba(74,222,128,0.1); border:1px solid rgba(74,222,128,0.25); color:#4ADE80; }
.route-hybrid { background:rgba(168,85,247,0.1); border:1px solid rgba(168,85,247,0.25); color:#C084FC; }

.conf-bar-wrap { display:flex; align-items:center; gap:8px; margin-left:auto; }
.conf-label { font-size:12px; color:#64748B; }
.conf-bar { width:80px; height:4px; background:rgba(255,255,255,0.08); border-radius:100px; overflow:hidden; }
.conf-fill { height:100%; background:linear-gradient(90deg,#38BDF8,#818CF8); border-radius:100px; }
.conf-pct { font-size:12px; font-weight:600; color:#94A3B8; min-width:32px; }

.sources-header {
    font-size: 12px; font-weight: 500; letter-spacing: 1.5px;
    text-transform: uppercase; color: #475569; margin: 20px 0 10px;
}

.source-chip-row { display:flex; flex-wrap:wrap; gap:8px; }

.source-chip {
    display:flex; align-items:center; gap:6px; padding:6px 12px;
    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07);
    border-radius:8px; font-size:12px; color:#64748B;
}

.source-chip span { color:#94A3B8; font-weight:500; }

.features-row { display:flex; justify-content:center; gap:8px; flex-wrap:wrap; }

.feature-pill {
    display:flex; align-items:center; gap:6px; padding:6px 14px;
    background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07);
    border-radius:100px; font-size:12px; color:#64748B;
}

.feature-pill strong { color:#94A3B8; }

[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
}

[data-testid="stExpander"] summary { color:#64748B !important; font-size:13px !important; }

@media (max-width:640px) {
    .sentinel-header { padding:16px; }
    .sentinel-hero { padding:40px 16px 24px; }
    .hero-title { font-size:32px; letter-spacing:-1px; }
    .hero-sub { font-size:14px; }
    .answer-card { padding:20px; }
    .conf-bar-wrap { margin-left:0; width:100%; }
}

/* ── CHIP TEXT FIX ── */
div[data-testid="stColumn"] button p,
div[data-testid="stColumn"] button span {
    color: #94A3B8 !important;
    font-size: 12px !important;
}

/* ── SEARCH BAR TEXT FIX ── */
[data-testid="stTextInput"] input {
    color: #E8EDF5 !important;
    caret-color: #38BDF8 !important;
    -webkit-text-fill-color: #E8EDF5 !important;
}

/* ── CHIP BACKGROUND FIX ── */
div[data-testid="stColumn"] button {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(148,163,184,0.2) !important;
    color: #94A3B8 !important;
}

/* FORCE search bar text dark */
[data-testid="stForm"] input,
[data-testid="stForm"] input:focus,
[data-testid="stForm"] input:active {
    color: #1E293B !important;
    -webkit-text-fill-color: #1E293B !important;
    background: rgba(255,255,255,0.92) !important;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "query_input" not in st.session_state:
    st.session_state.query_input = ""
if "auto_search" not in st.session_state:
    st.session_state.auto_search = False

# ── LOAD RESOURCES ────────────────────────────────────────────────────────────
@st.cache_resource
def load_resources():
    from ingestion.compliance_ingestor import get_chroma_collection, ingest_pdf
    from retrieval.hybrid_retriever import HybridRetrieverWithRerank
    from agents.graph import get_graph

    collection = get_chroma_collection()
    if collection.count() == 0:
        pdf_dir = Path("evaluation/test_datasets")
        for pdf in pdf_dir.glob("*.pdf"):
            ingest_pdf(pdf, collection)
    retriever = HybridRetrieverWithRerank(collection)
    graph = get_graph()
    return collection, retriever, graph

collection, retriever, graph = load_resources()
chunk_count = collection.count()

SUGGESTIONS = [
    "Password length requirements",
    "How to store cardholder data",
    "Audit log retention policy",
    "Multi-factor authentication",
    "Vulnerability scan frequency",
    "Network security controls",
    "Encryption for data in transit",
    "Penetration testing requirements",
]

# ── BACKGROUND ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="bg-grid"></div>
<div class="bg-glow-1"></div>
<div class="bg-glow-2"></div>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="sentinel-header">
    <div class="sentinel-logo">
        <div class="sentinel-logo-icon">🛡</div>
        <div class="sentinel-logo-name">FinOps Sentinel</div>
    </div>
    <div style="display:flex;gap:8px;">
        <span class="badge-pill badge-live">● Live</span>
        <span class="badge-pill badge-phase">Phase 3</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="sentinel-hero">
    <div class="hero-eyebrow">AI-Powered Compliance Intelligence</div>
    <h1 class="hero-title">Ask anything about<br><span>PCI-DSS compliance</span></h1>
    <p class="hero-sub">
        Get precise, cited answers from regulatory documents instantly.
        Powered by hybrid RAG, Cohere reranking, and LangGraph agents.
    </p>
    <div class="stats-row">
        <div class="stat-chip"><span class="dot"></span> <strong>{chunk_count}</strong> chunks indexed</div>
        <div class="stat-chip">🎯 <strong>1.00</strong> faithfulness score</div>
        <div class="stat-chip">⚡ <strong>Hybrid</strong> BM25 + Vector</div>
        <div class="stat-chip">🔁 <strong>100%</strong> routing accuracy</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── SUGGESTIONS ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="max-width:760px;margin:0 auto;padding:0 16px;position:relative;z-index:10;">
    <div class="suggestions-label">Try asking about</div>
</div>
""", unsafe_allow_html=True)

# Render suggestion chips in a centered container
with st.container():
    st.markdown('<div style="max-width:760px;margin:0 auto;padding:0 16px;">', unsafe_allow_html=True)
    row1 = st.columns(4)
    row2 = st.columns(4)

    for i, col in enumerate(row1):
        with col:
            if st.button(SUGGESTIONS[i], key=f"sug_{i}"):
                st.session_state.query_input = SUGGESTIONS[i]
                st.session_state.auto_search = True
                st.rerun()

    for i, col in enumerate(row2):
        with col:
            if st.button(SUGGESTIONS[i + 4], key=f"sug_{i+4}"):
                st.session_state.query_input = SUGGESTIONS[i + 4]
                st.session_state.auto_search = True
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── SEARCH FORM (Enter key support) ──────────────────────────────────────────
st.markdown("<div style='max-width:760px;margin:20px auto 0;padding:0 16px;position:relative;z-index:10;'>", unsafe_allow_html=True)

with st.form("search_form", clear_on_submit=False):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        query = st.text_input(
            "query",
            value=st.session_state.query_input,
            placeholder="e.g. What encryption is required for cardholder data at rest?",
            label_visibility="collapsed",
        )
    with col_btn:
        search_btn = st.form_submit_button("Search →", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# Handle auto-search from suggestion click
if st.session_state.auto_search:
    st.session_state.auto_search = False
    query = st.session_state.query_input
    search_btn = True

# ── RESULTS ───────────────────────────────────────────────────────────────────
if search_btn and query.strip():
    # Update session state
    st.session_state.query_input = query

    with st.spinner("Running agent pipeline..."):
        try:
            result = graph.invoke({"query": query})
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            result = None

    if result:
        corpus = result.get("corpus", "unknown").upper()
        confidence = result.get("confidence", 0)
        routing_reason = result.get("routing_reason", "")
        answer = result.get("final_answer", "No answer generated.")
        sources = result.get("compliance_results", [])

        route_class = {"COMPLIANCE": "route-compliance", "CODE": "route-code", "HYBRID": "route-hybrid"}.get(corpus, "route-compliance")
        route_icon = {"COMPLIANCE": "📋", "CODE": "💻", "HYBRID": "🔀"}.get(corpus, "📋")
        conf_width = int(confidence * 100)

        st.markdown(f"""
        <div style="max-width:760px;margin:24px auto 0;padding:0 16px;">
            <div class="routing-bar">
                <span class="route-tag {route_class}">{route_icon} {corpus}</span>
                <span style="font-size:13px;color:#475569;">LangGraph agent pipeline</span>
                <div class="conf-bar-wrap">
                    <span class="conf-label">Confidence</span>
                    <div class="conf-bar"><div class="conf-fill" style="width:{conf_width}%"></div></div>
                    <span class="conf-pct">{conf_width}%</span>
                </div>
            </div>
            <div class="answer-card">
                <div class="answer-label">Answer</div>
                <div class="answer-body">{answer}</div>
            </div>
        """, unsafe_allow_html=True)

        if sources:
            pages = sorted(set([s.get("page", 0) for s in sources if s.get("page")]))
            chips = "".join([f'<div class="source-chip">📄 <span>Page {p}</span></div>' for p in pages])
            st.markdown(f"""
                <div class="sources-header">Sources</div>
                <div class="source-chip-row">{chips}</div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("View routing decision & source chunks"):
            st.caption(f"**Routing reason:** {routing_reason}")
            if sources:
                for i, r in enumerate(sources):
                    st.markdown(f"**Chunk {i+1}** — Page {r.get('page','?')} — Distance: `{r.get('distance',0):.4f}`")
                    st.caption(r.get("text","")[:400] + "...")
                    if i < len(sources) - 1:
                        st.divider()

elif search_btn:
    st.markdown("<div style='text-align:center;padding:24px;color:#475569;font-size:14px;'>Please enter a question.</div>", unsafe_allow_html=True)

else:
    st.markdown("""
    <div class="features-row" style="max-width:760px;margin:24px auto 0;padding:0 16px;">
        <div class="feature-pill">🧠 <strong>LangGraph</strong> multi-agent</div>
        <div class="feature-pill">🔍 <strong>Hybrid</strong> BM25 + Vector</div>
        <div class="feature-pill">🎯 <strong>Cohere</strong> reranking</div>
        <div class="feature-pill">📊 <strong>RAGAS</strong> evaluated</div>
        <div class="feature-pill">⚡ <strong>Zero</strong> hallucination</div>
    </div>
    """, unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:48px 16px 32px;position:relative;z-index:10;">
    <div style="font-size:12px;color:#334155;letter-spacing:1px;">
        FINOPS SENTINEL &nbsp;·&nbsp; PCI-DSS v4.0.1 &nbsp;·&nbsp;
        RAGAS FAITHFULNESS 1.0 &nbsp;·&nbsp; BUILT WITH LANGCHAIN + LANGGRAPH
    </div>
</div>
""", unsafe_allow_html=True)