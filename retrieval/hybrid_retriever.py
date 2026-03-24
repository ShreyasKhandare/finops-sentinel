"""
FinOps Sentinel — Hybrid Retrieval Pipeline
Phase 2: BM25 + Vector search combined via Reciprocal Rank Fusion
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from rank_bm25 import BM25Okapi
from loguru import logger
import chromadb


# ── BM25 INDEX ────────────────────────────────────────────────────────────────
class BM25Index:
    def __init__(self, collection: chromadb.Collection):
        logger.info("Building BM25 index from Chroma collection...")
        all_docs = collection.get(include=["documents", "metadatas"])
        self.documents = all_docs["documents"]
        self.metadatas = all_docs["metadatas"]
        self.ids = all_docs["ids"]

        if not self.documents:
            logger.warning("BM25: empty corpus — index disabled")
            self.bm25 = None
            return

        tokenised = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(tokenised)
        logger.success(f"BM25 index built — {len(self.documents)} documents")

    def search(self, query: str, n_results: int = 20) -> list[dict]:
        if not self.bm25 or not self.documents:
            return []

        import numpy as np
        tokenised_query = query.lower().split()
        scores = self.bm25.get_scores(tokenised_query)
        top_indices = np.argsort(scores)[::-1][:n_results]

        results = []
        for rank, idx in enumerate(top_indices):
            results.append({
                "text": self.documents[idx],
                "source": self.metadatas[idx].get("source", "unknown"),
                "page": self.metadatas[idx].get("page_number", 0),
                "bm25_score": float(scores[idx]),
                "bm25_rank": rank,
                "id": self.ids[idx],
            })
        return results


# ── RECIPROCAL RANK FUSION ────────────────────────────────────────────────────
def reciprocal_rank_fusion(
    bm25_results: list[dict],
    vector_results: list[dict],
    k: int = 60,
    top_n: int = 10,
) -> list[dict]:
    scores: dict[str, float] = {}
    result_map: dict[str, dict] = {}

    for result in bm25_results:
        doc_id = result["id"]
        rank = result["bm25_rank"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (rank + k)
        result_map[doc_id] = result

    for rank, result in enumerate(vector_results):
        doc_id = result.get("id", f"vec_{rank}")
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (rank + k)
        if doc_id not in result_map:
            result_map[doc_id] = result

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    fused = []
    for doc_id in sorted_ids[:top_n]:
        result = result_map[doc_id].copy()
        result["rrf_score"] = round(scores[doc_id], 6)
        if "distance" not in result:
            result["distance"] = 0.5
        fused.append(result)

    return fused


# ── HYBRID RETRIEVER ──────────────────────────────────────────────────────────
class HybridRetriever:
    def __init__(self, collection: chromadb.Collection):
        self.collection = collection
        self.bm25_index = BM25Index(collection)
        logger.info("HybridRetriever ready")

    def search(
        self,
        query: str,
        n_results: int = 5,
        bm25_candidates: int = 20,
        vector_candidates: int = 20,
    ) -> list[dict]:
        logger.debug(f"Hybrid search: '{query[:60]}'")

        bm25_results = self.bm25_index.search(query, n_results=bm25_candidates)

        try:
            vector_raw = self.collection.query(
                query_texts=[query],
                n_results=vector_candidates,
            )
            vector_results = []
            for i in range(len(vector_raw["documents"][0])):
                vector_results.append({
                    "text": vector_raw["documents"][0][i],
                    "source": vector_raw["metadatas"][0][i].get("source", "unknown"),
                    "page": vector_raw["metadatas"][0][i].get("page_number", 0),
                    "distance": float(vector_raw["distances"][0][i]),
                    "id": vector_raw["ids"][0][i],
                })
        except Exception as e:
            logger.warning(f"Vector search failed: {e} — using BM25 only")
            vector_results = []

        if not bm25_results and not vector_results:
            return []

        fused = reciprocal_rank_fusion(
            bm25_results,
            vector_results,
            top_n=n_results,
        )

        logger.debug(f"Hybrid search returned {len(fused)} results")
        return fused


# ── HYBRID RETRIEVER WITH RERANK ──────────────────────────────────────────────
class HybridRetrieverWithRerank(HybridRetriever):
    def __init__(self, collection: chromadb.Collection):
        super().__init__(collection)
        import cohere
        self.cohere_client = cohere.Client(os.getenv("COHERE_API_KEY"))
        logger.info("HybridRetrieverWithRerank ready — Cohere Rerank v3 enabled")

    def search(
        self,
        query: str,
        n_results: int = 5,
        bm25_candidates: int = 30,
        vector_candidates: int = 30,
    ) -> list[dict]:

        try:
            fused = super().search(
                query,
                n_results=20,
                bm25_candidates=bm25_candidates,
                vector_candidates=vector_candidates,
            )
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            fused = []

        if not fused:
            # Fallback: pure vector search
            try:
                vector_raw = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                )
                return [{
                    "text": vector_raw["documents"][0][i],
                    "source": vector_raw["metadatas"][0][i].get("source", "unknown"),
                    "page": vector_raw["metadatas"][0][i].get("page_number", 0),
                    "distance": float(vector_raw["distances"][0][i]),
                    "id": vector_raw["ids"][0][i],
                } for i in range(len(vector_raw["documents"][0]))]
            except Exception as e2:
                logger.error(f"Fallback vector search also failed: {e2}")
                return []

        # Cohere reranking
        try:
            docs_to_rerank = [r["text"] for r in fused]
            rerank_response = self.cohere_client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=docs_to_rerank,
                top_n=n_results,
            )

            reranked = []
            for hit in rerank_response.results:
                result = fused[hit.index].copy()
                result["rerank_score"] = round(float(hit.relevance_score), 4)
                result["distance"] = round(1 - float(hit.relevance_score), 4)
                reranked.append(result)

            logger.debug(f"Reranked {len(fused)} to {len(reranked)} results")
            return reranked

        except Exception as e:
            logger.warning(f"Cohere reranking failed: {e} — using RRF order")
            for r in fused:
                if "distance" not in r:
                    r["distance"] = 0.5
            return fused[:n_results]