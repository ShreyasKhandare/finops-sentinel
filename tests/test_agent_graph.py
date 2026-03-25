"""
FinOps Sentinel — Agent Graph Integration Tests
End-to-end tests through the full LangGraph pipeline.
"""

import sys
import pytest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


@pytest.fixture(scope="module")
def graph():
    from agents.graph import build_graph
    return build_graph()


class TestGraphOutput:
    """Verify the graph produces well-formed output."""

    def test_returns_final_answer(self, graph):
        result = graph.invoke({"query": "What are the PCI-DSS password requirements?"})
        assert "final_answer" in result
        assert result["final_answer"]
        assert len(result["final_answer"]) > 50

    def test_returns_corpus_field(self, graph):
        result = graph.invoke({"query": "What are the PCI-DSS password requirements?"})
        assert "corpus" in result
        assert result["corpus"] in ["code", "compliance", "hybrid"]

    def test_returns_confidence(self, graph):
        result = graph.invoke({"query": "What are the PCI-DSS password requirements?"})
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    def test_returns_routing_reason(self, graph):
        result = graph.invoke({"query": "What are the PCI-DSS password requirements?"})
        assert "routing_reason" in result
        assert len(result["routing_reason"]) > 10

    def test_returns_source_chunks(self, graph):
        result = graph.invoke({"query": "What are the PCI-DSS password requirements?"})
        assert "compliance_results" in result
        assert len(result["compliance_results"]) > 0

    def test_source_chunks_have_page_numbers(self, graph):
        result = graph.invoke({"query": "What are the encryption requirements?"})
        for chunk in result.get("compliance_results", []):
            assert "page" in chunk
            assert chunk["page"] > 0


class TestAnswerQuality:
    """Test that answers contain expected content."""

    def test_password_answer_contains_length(self, graph):
        result = graph.invoke({"query": "What is the minimum password length in PCI-DSS?"})
        answer = result["final_answer"].lower()
        assert "12" in answer or "character" in answer, \
            f"Password answer missing length info: {answer[:200]}"

    def test_encryption_answer_contains_crypto_terms(self, graph):
        result = graph.invoke({"query": "What encryption is required for cardholder data?"})
        answer = result["final_answer"].lower()
        has_crypto = any(term in answer for term in [
            "cryptograph", "encrypt", "tls", "ssl", "strong", "aes"
        ])
        assert has_crypto, f"Encryption answer missing crypto terms: {answer[:200]}"

    def test_answer_contains_page_citations(self, graph):
        result = graph.invoke({"query": "What are the logging requirements under PCI-DSS?"})
        answer = result["final_answer"].lower()
        has_citation = "page" in answer or "requirement" in answer
        assert has_citation, f"Answer missing page citations: {answer[:200]}"

    def test_compliance_answer_has_requirement_numbers(self, graph):
        result = graph.invoke({"query": "What are the password security requirements?"})
        answer = result["final_answer"]
        # PCI-DSS requirement numbers follow pattern like "8.3.6" or "Requirement X"
        has_req = "requirement" in answer.lower() or any(
            f"{i}." in answer for i in range(1, 13)
        )
        assert has_req, f"Answer missing requirement numbers: {answer[:200]}"


class TestEdgeCases:
    """Test system behavior on unusual inputs."""

    def test_off_topic_query_does_not_crash(self, graph):
        """System should handle off-topic queries gracefully."""
        result = graph.invoke({"query": "What is the weather today?"})
        assert "final_answer" in result
        assert result["final_answer"]

    def test_very_specific_requirement_query(self, graph):
        result = graph.invoke({"query": "What does Requirement 8.3.6 say?"})
        assert "final_answer" in result
        answer = result["final_answer"].lower()
        assert "password" in answer or "8.3" in answer

    def test_code_query_returns_something(self, graph):
        """CODE queries should return an answer even without a code corpus."""
        result = graph.invoke({"query": "Which functions handle payment processing?"})
        assert "final_answer" in result
        assert result["corpus"] == "code"

    def test_hybrid_query_returns_something(self, graph):
        result = graph.invoke({
            "query": "Does our authentication code meet PCI-DSS Requirement 8?"
        })
        assert "final_answer" in result
        assert result["corpus"] == "hybrid"

    def test_no_error_field_on_success(self, graph):
        result = graph.invoke({"query": "What are the PCI-DSS password requirements?"})
        # Error field should be None or absent on successful queries
        error = result.get("error")
        assert error is None, f"Unexpected error on valid query: {error}"
