[README.md](https://github.com/user-attachments/files/26228503/README.md)
# FinOps Sentinel

**Dual-corpus RAG + multi-agent AI system for FinTech compliance intelligence**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://shreyas-finops-sentinel.streamlit.app)
[![API](https://img.shields.io/badge/API-Render-46E3B7?style=for-the-badge&logo=render)](https://finops-sentinel.onrender.com/docs)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.7-1C3C3C?style=for-the-badge)](https://langchain.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## What Is This?

FinOps Sentinel is an AI system that answers financial compliance questions with the accuracy and traceability that regulated industries actually need. You ask it something like *"What are the PCI-DSS requirements for storing cardholder data?"* and it gives you a structured answer with exact requirement numbers and page citations — grounded entirely in the actual regulatory documents, not in an LLM's training memory.

The system runs a LangGraph multi-agent pipeline under the hood: a classifier first figures out what kind of question you're asking (compliance regulation, codebase analysis, or both), then routes it to the right retrieval agent, which pulls the most relevant document chunks using hybrid BM25 + vector search, reranks them with Cohere, and finally generates a grounded answer using GPT-4o-mini.

The key differentiator is **measurable reliability**. Every design decision in this project was driven by RAGAS evaluation metrics, not intuition. Phase 1 started with a faithfulness score of 0.72 (meaning the LLM was hallucinating about 28% of the time). By Phase 2, after implementing hybrid retrieval and Cohere reranking, faithfulness hit **1.0** — zero hallucination on the evaluation suite.

---

## Live Demo

| Interface | URL | What You Can Do |
|-----------|-----|-----------------|
| **Visual UI** | [shreyas-finops-sentinel.streamlit.app](https://shreyas-finops-sentinel.streamlit.app) | Ask compliance questions, see routing decisions, view source citations |
| **REST API** | [finops-sentinel.onrender.com](https://finops-sentinel.onrender.com) | JSON responses with full metadata |
| **API Docs** | [finops-sentinel.onrender.com/docs](https://finops-sentinel.onrender.com/docs) | Interactive Swagger UI, try endpoints live |
| **Metrics** | [finops-sentinel.onrender.com/metrics](https://finops-sentinel.onrender.com/metrics) | Live RAGAS scores |

> **Note:** The API runs on Render's free tier, so the first request after inactivity may take 30-60 seconds to wake up. Subsequent requests are fast.

---

## RAGAS Evaluation Results

These numbers were measured objectively using the RAGAS framework on 8 hand-crafted PCI-DSS test questions. The improvement from Phase 1 to Phase 2 is what the hybrid retrieval pipeline actually achieved — not claimed, measured.

| Metric | Phase 1 Baseline | Phase 2 (Hybrid + Rerank) | Change |
|--------|-----------------|---------------------------|--------|
| **Faithfulness** | 0.7188 | **1.0000** | +38.9% ✅ |
| **Answer Relevancy** | 0.6591 | **0.8773** | +33.1% ✅ |
| **Context Precision** | 0.8437 | **0.9599** | +13.8% ✅ |
| **Context Recall** | 0.7604 | **0.7604** | maintained ✅ |

**Faithfulness = 1.0** means every claim in every generated answer is directly traceable to a retrieved document chunk. No hallucination.

The root cause diagnosis was interesting: prompt engineering alone had zero effect on faithfulness. The problem was retrieval quality, not generation. Fixing retrieval (hybrid BM25 + vector + reranking) fixed faithfulness.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────────────┐
│   QueryClassifier   │  GPT-4o-mini, structured JSON output
│   (LangGraph Node)  │  Routes: CODE | COMPLIANCE | HYBRID
└─────────┬───────────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
┌────────┐  ┌──────────────────┐
│  Code  │  │ ComplianceMapper │  Hybrid BM25 + Vector retrieval
│Analyzer│  │  (LangGraph Node)│  Cohere Rerank v3
│(Phase 4│  └────────┬─────────┘
│  TBD)  │           │
└────────┘           ▼
                ┌────────────┐
                │   Format   │  GPT-4o-mini, temperature=0
                │  Response  │  Strict faithfulness prompt
                └────────────┘
                     │
                     ▼
             Structured Answer
             + Page Citations
             + Source Chunks
             + Routing Metadata
```

### Retrieval Pipeline (Phase 2)

```
Query
  │
  ├──► BM25 Search (30 candidates)    ← exact keyword matching
  │
  ├──► Vector Search (30 candidates)  ← semantic similarity
  │         (ChromaDB + all-MiniLM-L6-v2 locally,
  │          OpenAI text-embedding-3-small in production)
  │
  ├──► RRF Fusion                     ← merges both ranked lists
  │       score = 1/(rank + 60)
  │
  └──► Cohere Rerank v3 (top 5)       ← cross-encoder reranking
           model: rerank-english-v3.0
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Orchestration** | LangGraph 0.2.45 | Explicit state machine with conditional routing — more controllable than AgentExecutor |
| **LLM Framework** | LangChain 0.3.7 | Standardized abstractions for LLM calls, prompt templates, output parsers |
| **LLM** | GPT-4o-mini | Strong instruction following at low cost. Temperature=0 for deterministic compliance answers |
| **Vector Store** | ChromaDB 0.5.15 | Zero-config persistent storage for development; easy swap to Pinecone for production |
| **Embeddings** | all-MiniLM-L6-v2 (local) / text-embedding-3-small (prod) | Local model for dev to avoid API costs; OpenAI for production quality |
| **Keyword Search** | rank-bm25 0.2.2 | Handles exact regulatory terminology (article numbers, defined terms) that vector search misses |
| **Reranking** | Cohere Rerank v3 | Cross-encoder reranking dramatically improves result ordering over bi-encoder retrieval |
| **Evaluation** | RAGAS 0.2.5 | Objective, reproducible measurement of faithfulness, relevancy, precision, recall |
| **PDF Parsing** | PyMuPDF 1.24.9 | Fast, accurate extraction of text from regulatory PDFs with page number metadata |
| **API** | FastAPI 0.115.4 | Async by default, Pydantic validation, auto-generated OpenAPI docs |
| **UI** | Streamlit 1.40.0 | Rapid prototyping for ML demos without frontend overhead |
| **Tracing** | LangSmith | Full observability into every node execution, token costs, latency |

---

## Project Structure

```
finops-sentinel/
│
├── agents/                     # LangGraph agent nodes
│   ├── state.py                # AgentState TypedDict schema
│   ├── query_classifier.py     # GPT-4o-mini 3-way router
│   ├── compliance_mapper.py    # Compliance retrieval + analysis node
│   └── graph.py                # StateGraph assembly and compilation
│
├── ingestion/
│   └── compliance_ingestor.py  # PDF parsing, chunking, ChromaDB ingestion
│
├── retrieval/
│   ├── hybrid_retriever.py     # BM25 + vector + RRF + Cohere rerank
│   └── prompt_templates.py     # Strict faithfulness prompts
│
├── evaluation/
│   ├── ragas_eval.py           # 8-question RAGAS evaluation suite
│   ├── test_datasets/          # PCI-DSS v4.0.1 PDF
│   └── results/                # Saved evaluation JSON results
│
├── api/
│   └── main.py                 # FastAPI backend (4 endpoints)
│
├── ui/
│   └── app.py                  # Streamlit frontend
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── docs/
│   ├── BUILD_LOG.md            # Full session-by-session build history
│   └── METRICS.md              # All benchmark numbers with timestamps
│
├── requirements.txt            # Production (slim, no torch)
├── requirements-dev.txt        # Full local development
├── render.yaml                 # Render deployment config
├── runtime.txt                 # Python 3.11 for Streamlit Cloud
└── .python-version             # Python 3.11.9 for Render
```

---

## Running Locally

### Prerequisites

- Python 3.11.x (specifically — 3.12+ has compatibility issues with some dependencies)
- Git Bash or any Unix-like terminal on Windows

### Setup

```bash
# Clone the repo
git clone https://github.com/ShreyasKhandare/finops-sentinel.git
cd finops-sentinel

# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements-dev.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-openai-key
COHERE_API_KEY=your-cohere-key
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=finops-sentinel
ENVIRONMENT=development
```

You need accounts for:
- [OpenAI](https://platform.openai.com) — ~$0.10-0.15 per full RAGAS evaluation run
- [Cohere](https://dashboard.cohere.com) — free trial tier is sufficient
- [LangSmith](https://smith.langchain.com) — free tier

### Ingest the Compliance Corpus

```bash
python ingestion/compliance_ingestor.py
```

This parses the PCI-DSS v4.0.1 PDF, creates 413 chunks, and stores them in ChromaDB. Takes about 3 minutes on first run (downloads the embedding model).

### Run the Streamlit UI

```bash
streamlit run ui/app.py
```

Opens at `http://localhost:8501`

### Run the FastAPI Backend

```bash
uvicorn api.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`

### Run RAGAS Evaluation

```bash
python evaluation/ragas_eval.py
```

Takes 3-5 minutes, costs ~$0.15 in OpenAI credits. Results saved to `evaluation/results/`.

---

## API Reference

### POST /query

The main endpoint. Runs the full LangGraph pipeline.

**Request:**
```json
{
  "query": "What are the PCI-DSS requirements for password security?",
  "n_results": 5
}
```

**Response:**
```json
{
  "query": "What are the PCI-DSS requirements for password security?",
  "corpus": "compliance",
  "confidence": 0.95,
  "routing_reason": "Query asks about PCI-DSS regulations, falls under compliance",
  "answer": "REQUIREMENTS FOUND:\n- Requirement 8.3.6: Passwords must be...",
  "sources": [
    {
      "source": "PCI-DSS-v4_0_1.pdf",
      "page": 194,
      "text": "Strong passwords/passphrases...",
      "distance": 0.0042
    }
  ],
  "latency_ms": 4823.5,
  "timestamp": "2026-03-24T02:17:28.000Z"
}
```

### GET /health

```json
{
  "status": "healthy",
  "version": "0.4.0",
  "corpus_chunks": 413,
  "agent_graph": "active"
}
```

### GET /metrics

Returns the latest RAGAS evaluation scores.

---

## Compliance Corpus

Currently indexed:

| Document | Version | Chunks | Coverage |
|----------|---------|--------|----------|
| PCI-DSS | v4.0.1 | 413 | Full document (360 pages) |

**Planned additions:**
- DORA (Digital Operational Resilience Act)
- SEC Cybersecurity Disclosure Rules
- SOC 2 Type II criteria

Adding a new document takes one command:
```bash
# Drop any PDF into evaluation/test_datasets/ and re-run
python ingestion/compliance_ingestor.py
```

---

## Design Decisions Worth Explaining

**Why LangGraph instead of LangChain's AgentExecutor?**

AgentExecutor is a loop that runs until the LLM decides to stop — you have limited visibility into what's happening and can't easily add custom logic between steps. LangGraph gives an explicit state machine where every node, transition, and conditional edge is defined in code. For a system that needs to route queries to different retrieval pipelines and combine results, that explicit control matters.

**Why hybrid BM25 + vector instead of pure vector search?**

Pure vector search has a blind spot: exact terminology. If a regulation says "Requirement 9.4.2" and a user queries "Requirement 9.4.2", the vector search might not surface it at the top because vectors capture semantic similarity, not exact matches. BM25 excels at exact term matching. The combination — merged with RRF — gets the best of both. The RAGAS numbers validated this: faithfulness jumped from 0.72 to 1.0.

**Why Cohere Rerank on top of hybrid retrieval?**

The initial retrieval pulls 20-30 candidates from each source. A cross-encoder reranker (Cohere) then re-scores all candidates together against the query — it reads the full chunk text alongside the query, which is much more accurate than the bi-encoder embeddings used for initial retrieval. It's computationally expensive to run across the whole corpus, but cheap and effective as a final reranking step over a small candidate set.

**Why temperature=0 for the LLM?**

Compliance is not a domain for creativity. The same query should produce the same answer every time. Temperature=0 makes the generation deterministic and makes the system testable — you can run the same eval query 10 times and get consistent results.

---

## Evaluation Methodology

The RAGAS evaluation suite in `evaluation/ragas_eval.py` tests 8 compliance questions with hand-written ground truth answers. Each question covers a different PCI-DSS domain: password security, encryption, access control, logging, vulnerability management, network security, authentication, and data storage.

The evaluation uses GPT-4o-mini as the judge for all four metrics, with OpenAI text-embedding-3-small for answer relevancy computation. Results are saved as timestamped JSON files so you can track improvement across phases.

To compare phases:
```bash
# Run baseline
python evaluation/ragas_eval.py  # label: phase1_baseline

# Make changes, then run again
python evaluation/ragas_eval.py  # label: phase2_hybrid
```

---

## Build Log

The complete session-by-session build history — every error, fix, and decision — is documented in [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md). If you want to understand why specific architectural choices were made, that's where to look.

All RAGAS scores with timestamps are in [`docs/METRICS.md`](docs/METRICS.md).

---

## What's Next

- **Code corpus ingestion** — AST-based chunking of a FinTech open-source codebase (ccxt or freqtrade) using tree-sitter, function-level chunks
- **CodeAnalyzer agent** — retrieval from the code corpus, returning affected functions and file paths
- **HybridSynthesizer** — cross-corpus queries that map code findings to compliance requirements with dual citations
- **Pinecone migration** — swap ChromaDB for Pinecone in production for persistent, scalable vector storage

---

## Author

**Shreyas Khandare**

Building FinOps Sentinel as an AI engineering portfolio project targeting AI Engineer / LLM Engineer / RAG Engineer roles at FinTech and RegTech companies.

- GitHub: [@ShreyasKhandare](https://github.com/ShreyasKhandare)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
