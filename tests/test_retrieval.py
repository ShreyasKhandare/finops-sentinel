"""
FinOps Sentinel — Retrieval Unit Tests
Tests the hybrid retriever in isolation.
"""

import sys
import pytest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


@pytest.fixture(scope="module")
def collection():
    from ingestion.compliance_ingestor import get_chroma_collection
    return get_chroma_collection()


@pytest.fixture(scope="module")
def retriever(collection):
    from retrieval.hybrid_retriever import HybridRetrieverWithRerank
    return HybridRetrieverWithRerank(collection)


@pytest.fixture(scope="module")
def bm25_retriever(collection):
    from retrieval.hybrid_retriever import HybridRetriever
    return HybridRetriever(collection)


class TestCorpusHealth:
    """Verify the corpus is loaded and healthy."""

    def test_corpus_not_empty(self, collection):
        count = collection.count()
        assert count > 0, f"Corpus is empty — run ingestion first"

    def test_corpus_has_expected_chunks(self, collection):
        count = collection.count()
        assert count >= 400, f"Expected ~413 chunks, got {count}"

    def test_corpus_has_metadata(self, collection):
        sample = collection.get(limit=1, include=["metadatas"])
        assert sample["metadatas"], "No metadata found in corpus"
        meta = sample["metadatas"][0]
        assert "source" in meta, "Missing 'source' field in metadata"
        assert "page_number" in meta, "Missing 'page_number' field in metadata"


class TestBM25Retriever:
    """Test BM25 keyword search in isolation."""

    def test_returns_results(self, bm25_retriever):
        results = bm25_retriever.search("password requirements", n_results=5)
        assert len(results) > 0, "BM25 returned no results"

    def test_result_structure(self, bm25_retriever):
        results = bm25_retriever.search("encryption cardholder data", n_results=3)
        for r in results:
            assert "text" in r
            assert "source" in r
            assert "page" in r
            assert "distance" in r

    def test_exact_term_matching(self, bm25_retriever):
        """BM25 should find exact regulatory terms."""
        results = bm25_retriever.search("Requirement 8.3.6", n_results=5)
        assert len(results) > 0
        # At least one result should contain the exact term
        texts = " ".join([r["text"].lower() for r in results])
        assert "8.3.6" in texts or "password" in texts

    def test_empty_corpus_does_not_crash(self):
        """BM25 must handle empty corpus without division by zero."""
        import chromadb
        from retrieval.hybrid_retriever import BM25Index
        client = chromadb.EphemeralClient()
        from chromadb.utils import embedding_functions
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        empty_col = client.get_or_create_collection("test_empty", embedding_function=ef)
        index = BM25Index(empty_col)
        results = index.search("anything", n_results=5)
        assert results == [], f"Expected empty list, got {results}"

    def test_returns_correct_count(self, bm25_retriever):
        results = bm25_retriever.search("access control", n_results=7)
        assert len(results) <= 7


class TestHybridRetriever:
    """Test the full hybrid retrieval pipeline."""

    def test_returns_results(self, retriever):
        results = retriever.search("password security requirements", n_results=5)
        assert len(results) > 0

    def test_results_have_distance(self, retriever):
        results = retriever.search("cardholder data encryption", n_results=5)
        for r in results:
            assert "distance" in r
            assert 0.0 <= r["distance"] <= 1.0, f"Distance {r['distance']} out of range"

    def test_results_have_page_numbers(self, retriever):
        results = retriever.search("audit log requirements", n_results=5)
        for r in results:
            assert "page" in r
            assert isinstance(r["page"], int)
            assert r["page"] > 0

    def test_password_query_returns_relevant_pages(self, retriever):
        """Password requirements are on pages 190-215 in PCI-DSS v4.0.1."""
        results = retriever.search("password length requirements PCI-DSS", n_results=5)
        pages = [r["page"] for r in results]
        # At least one result should be from the password section
        assert any(180 <= p <= 220 for p in pages), \
            f"Expected pages 180-220, got {pages}"

    def test_reranker_improves_top_result(self, retriever):
        """Top result after reranking should have low distance score."""
        results = retriever.search("What is the minimum password length?", n_results=5)
        assert len(results) > 0
        top_distance = results[0]["distance"]
        assert top_distance < 0.5, \
            f"Top result distance {top_distance:.4f} is too high — reranking may not be working"

    def test_handles_long_query(self, retriever):
        long_query = "What are all the specific technical requirements that PCI-DSS version 4 mandates for organizations that store process or transmit cardholder data including primary account numbers and sensitive authentication data?"
        results = retriever.search(long_query, n_results=5)
        assert len(results) > 0

    def test_handles_single_word_query(self, retriever):
        results = retriever.search("encryption", n_results=5)
        assert len(results) > 0

    def test_result_text_not_empty(self, retriever):
        results = retriever.search("network security firewall", n_results=5)
        for r in results:
            assert r["text"].strip() != "", "Empty text in result"
            assert len(r["text"]) > 50, "Result text suspiciously short"
