"""
FinOps Sentinel — Hybrid Retrieval Pipeline
Phase 2: BM25 + Vector search combined via Reciprocal Rank Fusion

Why hybrid:
- Vector search: finds semantically similar content
- BM25: finds exact keyword matches (article numbers, defined terms)
- Combined: best of both worlds, measurably better recall
"""
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from rank_bm25 import BM25Okapi
from loguru import logger
import chromadb
from chromadb.utils import embedding_functions


# ── BM25 INDEX ────────────────────────────────────────────────────────────────
class BM25Index:
    """
    Builds and queries a BM25 keyword index over the compliance corpus.
    Rebuilt from Chroma on each instantiation — fast enough for dev.
    """

    def __init__(self, collection: chromadb.Collection):
        """
        Build BM25 index from all documents in a Chroma collection.

        Args:
            collection: Chroma collection to index
        """
        logger.info("Building BM25 index from Chroma collection...")

        # Fetch all documents from Chroma
        all_docs = collection.get(include=["documents", "metadatas"])
        self.documents = all_docs["documents"]
        self.metadatas = all_docs["metadatas"]
        self.ids = all_docs["ids"]

        # Tokenise for BM25
        tokenised = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(tokenised)

        logger.success(f"BM25 index built — {len(self.documents)} documents")

    def search(self, query: str, n_results: int = 20) -> list[dict]:
        """
        Search the BM25 index.

        Args:
            query: Search query string
            n_results: Number of results to return

        Returns:
            List of dicts with text, metadata, bm25_score, bm25_rank
        """
        tokenised_query = query.lower().split()
        scores = self.bm25.get_scores(tokenised_query)

        # Get top N indices
        import numpy as np
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
    """
    Merge BM25 and vector results using Reciprocal Rank Fusion.

    RRF score = 1/(rank + k) for each result list, summed.
    Higher score = appears near top of both lists.

    Args:
        bm25_results: Results from BM25 search (with bm25_rank)
        vector_results: Results from vector search (with distance)
        k: RRF constant (60 is standard)
        top_n: Number of final results to return

    Returns:
        Merged and re-ranked list of results
    """
    scores: dict[str, float] = {}
    result_map: dict[str, dict] = {}

    # Score BM25 results
    for result in bm25_results:
        doc_id = result["id"]
        rank = result["bm25_rank"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (rank + k)
        result_map[doc_id] = result

    # Score vector results
    for rank, result in enumerate(vector_results):
        doc_id = result.get("id", f"vec_{rank}")
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (rank + k)
        if doc_id not in result_map:
            result_map[doc_id] = result

    # Sort by combined RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    fused = []
    for doc_id in sorted_ids[:top_n]:
        result = result_map[doc_id].copy()
        result["rrf_score"] = round(scores[doc_id], 6)
        fused.append(result)

    return fused


# ── MAIN HYBRID RETRIEVER ─────────────────────────────────────────────────────
class HybridRetriever:
    """
    Combined BM25 + vector retriever with RRF merging.
    Drop-in replacement for pure vector search.
    """

    def __init__(self, collection: chromadb.Collection):
        """
        Initialise hybrid retriever with a Chroma collection.

        Args:
            collection: Chroma collection to search
        """
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
        """
        Hybrid search: BM25 + vector → RRF fusion → top N results.

        Args:
            query: Natural language query
            n_results: Final number of results to return
            bm25_candidates: How many BM25 candidates to consider
            vector_candidates: How many vector candidates to consider

        Returns:
            List of result dicts with text, source, page, rrf_score
        """
        logger.debug(f"Hybrid search: '{query[:60]}...'")

        # BM25 search
        bm25_results = self.bm25_index.search(query, n_results=bm25_candidates)

        # Vector search
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
                "distance": vector_raw["distances"][0][i],
                "id": vector_raw["ids"][0][i],
            })

        # RRF fusion
        fused = reciprocal_rank_fusion(
            bm25_results,
            vector_results,
            top_n=n_results,
        )

        logger.debug(f"Hybrid search returned {len(fused)} results")
        return fused
    
    # ── COHERE RERANKER ───────────────────────────────────────────────────────────
class HybridRetrieverWithRerank(HybridRetriever):
    """
    Hybrid retriever with Cohere Rerank v3 post-processing.
    Retrieves more candidates then reranks to top N.
    Fixes the recall drop from pure BM25 boosting.
    """

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
        """
        Hybrid search + Cohere reranking.
        Retrieves 30 candidates from each source, fuses to 20, reranks to n_results.
        """
        import os

        # Get more candidates than needed
        fused = super().search(
            query,
            n_results=20,
            bm25_candidates=bm25_candidates,
            vector_candidates=vector_candidates,
        )

        if not fused:
            return []

        # Rerank with Cohere
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
                result["rerank_score"] = round(hit.relevance_score, 4)
                result["distance"] = round(1 - hit.relevance_score, 4)
                reranked.append(result)

            logger.debug(f"Reranked {len(fused)} → {len(reranked)} results")
            return reranked

        except Exception as e:
            logger.warning(f"Cohere reranking failed: {e} — falling back to RRF order")
            return fused[:n_results]   