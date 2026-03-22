## Phase 1 COMPLETE — Official Metrics
**Date:** March 2026
**Status:** ✅ COMPLETE

### Retrieval Performance
| Metric | Value |
|---|---|
| Chunks in corpus | 413 |
| Top result distance | 0.6060 |
| Bottom result distance | 0.7383 |
| Baseline (first test) | 0.8385 |
| Improvement | +26.5% |

### Answer Quality (Manual Review)
| Check | Result |
|---|---|
| Correct regulation sections cited | ✅ Req 3.2, 3.2.1, 9.4 |
| Correct page numbers | ✅ Pages 81, 214, 225 |
| Structured output | ✅ Bullet points |
| No hallucination (manual check) | ✅ All claims traceable |
| I-don't-know fallback | ✅ Implemented |

### Phase 2 Targets (to beat)
| Metric | Current | Target |
|---|---|---|
| Top distance | 0.6060 | < 0.40 |
| RAGAS Faithfulness | Not measured | ≥ 0.88 |
| RAGAS Context Precision | Not measured | ≥ 0.82 |
| Hallucination rate | Not measured | < 8% |

## Phase 1 Baseline — RAGAS Official Scores
**Date:** 21 March 2026  
**Run file:** evaluation/results/phase1_baseline_20260321_2102.json

| Metric | Phase 1 Score | Target | Status |
|---|---|---|---|
| Faithfulness | 0.7188 | ≥ 0.88 | ❌ Gap: 0.16 |
| Answer Relevancy | 0.6591 | ≥ 0.84 | ❌ Gap: 0.18 |
| Context Precision | 0.8437 | ≥ 0.80 | ✅ Passing |
| Context Recall | 0.7604 | ≥ 0.75 | ✅ Passing |

### Diagnosis
- Retrieval layer is working well (precision + recall both pass)
- Generation layer is the problem (faithfulness + relevancy both fail)
- LLM is adding content beyond retrieved chunks (hallucination)
- Fix: stricter system prompt + Cohere reranking in Phase 2

### Phase 2 Targets
| Metric | Current | Target | Required Improvement |
|---|---|---|---|
| Faithfulness | 0.7188 | ≥ 0.88 | +0.16 |
| Answer Relevancy | 0.6591 | ≥ 0.84 | +0.18 |
| Context Precision | 0.8437 | ≥ 0.80 | maintain |
| Context Recall | 0.7604 | ≥ 0.75 | maintain |

## Phase 2 — Hybrid Retrieval Results
**Date:** 21 March 2026
**Run file:** evaluation/results/phase2_hybrid_retrieval_20260321_2129.json

| Metric | Phase 1 | Phase 2 | Delta | Status |
|---|---|---|---|---|
| Faithfulness | 0.7188 | 0.9643 | +0.2455 (+34.2%) | ✅ |
| Answer Relevancy | 0.6591 | 0.9191 | +0.2600 (+39.4%) | ✅ |
| Context Precision | 0.8437 | 0.9797 | +0.1360 (+16.1%) | ✅ |
| Context Recall | 0.7604 | 0.6562 | -0.1042 (-13.7%) | ❌ |

### Diagnosis
- Hybrid BM25+vector retrieval dramatically improved faithfulness
  and relevancy — the LLM now has better chunks to ground answers in
- Context recall dropped — BM25 boosts precision but misses
  semantically relevant chunks that lack exact keyword matches
- Fix: add Cohere Rerank to re-score and recover missed chunks

### Resume-Ready Metric
"Implemented hybrid BM25+vector retrieval — improved faithfulness
from 0.72 to 0.96 (+34%) and answer relevancy from 0.66 to 0.92
(+39%) over pure vector baseline"

## Phase 2 COMPLETE — Final Results with Reranking
**Date:** 21 March 2026
**Run:** evaluation/results/phase2_hybrid_rerank_20260321_2136.json

| Metric | Phase 1 | Phase 2 | Delta |
|---|---|---|---|
| Faithfulness | 0.7188 | 1.0000 | +38.9% |
| Answer Relevancy | 0.6591 | 0.8773 | +33.1% |
| Context Precision | 0.8437 | 0.9599 | +13.8% |
| Context Recall | 0.7604 | 0.7604 | 0.0% |

### Stack That Achieved This
- BM25 (rank-bm25) — keyword exact match layer
- ChromaDB vector search — semantic similarity layer  
- Reciprocal Rank Fusion — merges both result lists
- Cohere Rerank v3 (rerank-english-v3.0) — final reranking

### Status: ALL 4 METRICS PASSING ✅