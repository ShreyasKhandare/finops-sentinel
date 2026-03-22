"""
FinOps Sentinel - FastAPI Backend
Phase 4: Production API layer replacing direct Streamlit calls

Endpoints:
    POST /query     - Run agent graph on a query
    GET  /health    - Health check
    GET  /metrics   - System metrics
    GET  /corpus    - Corpus status
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ── APP SETUP ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FinOps Sentinel API",
    description="Dual-corpus RAG + multi-agent system for FinTech compliance",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allows Streamlit and future frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── REQUEST / RESPONSE SCHEMAS ────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language compliance or code question",
        example="What are the PCI-DSS requirements for password security?",
    )
    n_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of source chunks to retrieve",
    )


class SourceChunk(BaseModel):
    source: str
    page: int
    text: str
    distance: float


class QueryResponse(BaseModel):
    query: str
    corpus: str
    confidence: float
    routing_reason: str
    answer: str
    sources: list[SourceChunk]
    latency_ms: float
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    corpus_chunks: int
    agent_graph: str


class MetricsResponse(BaseModel):
    phase: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    corpus_chunks: int
    embedding_model: str
    retrieval_strategy: str


# ── STARTUP — load resources once ────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Load agent graph and corpus on startup."""
    logger.info("FinOps Sentinel API starting up...")
    try:
        from agents.graph import get_graph
        from ingestion.compliance_ingestor import get_chroma_collection
        app.state.graph = get_graph()
        app.state.collection = get_chroma_collection()
        logger.success("Agent graph and corpus loaded successfully")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and system status."""
    try:
        chunk_count = app.state.collection.count()
        graph_status = "active" if app.state.graph else "inactive"
    except Exception:
        chunk_count = 0
        graph_status = "error"

    return HealthResponse(
        status="healthy",
        version="0.4.0",
        timestamp=datetime.now().isoformat(),
        corpus_chunks=chunk_count,
        agent_graph=graph_status,
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Return latest RAGAS evaluation metrics."""
    return MetricsResponse(
        phase="Phase 2 - Hybrid RAG with Cohere Rerank",
        faithfulness=1.0,
        answer_relevancy=0.8773,
        context_precision=0.9599,
        context_recall=0.7604,
        corpus_chunks=413,
        embedding_model="all-MiniLM-L6-v2",
        retrieval_strategy="BM25 + Vector + Cohere Rerank v3",
    )


@app.get("/corpus")
async def corpus_status():
    """Return corpus information."""
    try:
        count = app.state.collection.count()
        return {
            "status": "ready",
            "collections": [
                {
                    "name": "compliance",
                    "chunks": count,
                    "documents": ["PCI-DSS v4.0.1"],
                    "embedding_model": "all-MiniLM-L6-v2",
                }
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Run the full agent pipeline on a query.

    Routes through LangGraph:
    QueryClassifier -> ComplianceMapper -> FormatResponse
    """
    start_time = time.time()
    logger.info(f"Query received: '{request.query[:60]}...'")

    try:
        # Run agent graph
        result = app.state.graph.invoke({
            "query": request.query,
        })

        # Extract results
        compliance_results = result.get("compliance_results", [])

        # Build source chunks
        sources = []
        for r in compliance_results[:request.n_results]:
            sources.append(SourceChunk(
                source=r.get("source", "unknown"),
                page=r.get("page", 0),
                text=r.get("text", "")[:500],
                distance=r.get("distance", 1.0),
            ))

        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.success(f"Query complete in {latency_ms}ms")

        return QueryResponse(
            query=request.query,
            corpus=result.get("corpus", "unknown"),
            confidence=result.get("confidence", 0.0),
            routing_reason=result.get("routing_reason", ""),
            answer=result.get("final_answer", "No answer generated."),
            sources=sources,
            latency_ms=latency_ms,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))