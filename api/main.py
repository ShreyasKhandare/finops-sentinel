"""
FinOps Sentinel - FastAPI Backend
Phase 4: Production API
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ── GLOBAL STATE ──────────────────────────────────────────────────────────────
graph = None
collection = None


# ── LIFESPAN ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global graph, collection
    logger.info("Starting up...")

    try:
        from ingestion.compliance_ingestor import get_chroma_collection
        collection = get_chroma_collection()
        logger.info(f"Collection loaded: {collection.count()} chunks")

        from agents.graph import get_graph
        graph = get_graph()
        logger.info("Graph loaded")

    except Exception as e:
        logger.error(f"Startup error: {e}")

    yield

    logger.info("Shutting down...")


# ── APP ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="FinOps Sentinel API",
    description="Dual-corpus RAG + multi-agent system for FinTech compliance",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── SCHEMAS ───────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    n_results: int = Field(default=5, ge=1, le=10)


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


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "FinOps Sentinel API",
        "version": "0.4.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    chunk_count = 0
    try:
        if collection:
            chunk_count = collection.count()
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": "0.4.0",
        "timestamp": datetime.now().isoformat(),
        "corpus_chunks": chunk_count,
        "agent_graph": "active" if graph else "loading",
    }


@app.get("/metrics")
async def metrics():
    return {
        "phase": "Phase 2 - Hybrid RAG with Cohere Rerank",
        "faithfulness": 1.0,
        "answer_relevancy": 0.8773,
        "context_precision": 0.9599,
        "context_recall": 0.7604,
        "corpus_chunks": 413,
        "embedding_model": "all-MiniLM-L6-v2",
        "retrieval_strategy": "BM25 + Vector + Cohere Rerank v3",
    }


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="System still initializing. Please retry in 30 seconds."
        )

    start_time = time.time()
    logger.info(f"Query: '{request.query[:60]}'")

    try:
        result = graph.invoke({"query": request.query})

        compliance_results = result.get("compliance_results", [])
        sources = [
            SourceChunk(
                source=r.get("source", "unknown"),
                page=r.get("page", 0),
                text=r.get("text", "")[:500],
                distance=r.get("distance", 1.0),
            )
            for r in compliance_results[:request.n_results]
        ]

        latency_ms = round((time.time() - start_time) * 1000, 2)

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