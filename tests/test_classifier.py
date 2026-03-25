"""
FinOps Sentinel — Query Classifier Unit Tests
Tests routing accuracy across all three corpus types.
"""

import sys
import pytest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agents.query_classifier import classify_query


class TestComplianceRouting:
    """Queries that should route to the compliance corpus."""

    @pytest.mark.parametrize("query", [
        "What are the PCI-DSS password requirements?",
        "What encryption is required for cardholder data?",
        "How long must audit logs be retained under PCI-DSS?",
        "What are the vulnerability scanning requirements?",
        "What does PCI-DSS require for multi-factor authentication?",
        "What are the network security requirements?",
        "How must physical access to cardholder data be controlled?",
        "What are the incident response requirements?",
    ])
    def test_routes_to_compliance(self, query):
        result = classify_query(query)
        assert result.corpus == "compliance", \
            f"Expected 'compliance', got '{result.corpus}' for: {query}"

    @pytest.mark.parametrize("query", [
        "What are the PCI-DSS password requirements?",
        "What encryption is required for cardholder data?",
        "How long must audit logs be retained under PCI-DSS?",
    ])
    def test_compliance_confidence_above_threshold(self, query):
        result = classify_query(query)
        assert result.confidence >= 0.85, \
            f"Confidence {result.confidence:.2f} too low for: {query}"


class TestCodeRouting:
    """Queries that should route to the code corpus."""

    @pytest.mark.parametrize("query", [
        "Which functions handle payment processing?",
        "Where is the authentication logic in the codebase?",
        "Show me the order processing functions",
        "What does the payment_service.py file do?",
        "Which modules handle card tokenization?",
    ])
    def test_routes_to_code(self, query):
        result = classify_query(query)
        assert result.corpus == "code", \
            f"Expected 'code', got '{result.corpus}' for: {query}"


class TestHybridRouting:
    """Queries that span both corpora."""

    @pytest.mark.parametrize("query", [
        "Does our authentication code meet PCI-DSS Requirement 8?",
        "Which functions in our codebase need to change for PCI-DSS compliance?",
        "Does our encryption implementation meet PCI-DSS requirements?",
        "What code changes does PCI-DSS Requirement 3.4 require?",
    ])
    def test_routes_to_hybrid(self, query):
        result = classify_query(query)
        assert result.corpus == "hybrid", \
            f"Expected 'hybrid', got '{result.corpus}' for: {query}"


class TestClassifierOutput:
    """Test the structure and quality of classifier output."""

    def test_returns_valid_corpus(self):
        result = classify_query("What are the password requirements?")
        assert result.corpus in ["code", "compliance", "hybrid"]

    def test_returns_confidence_between_0_and_1(self):
        result = classify_query("What are the password requirements?")
        assert 0.0 <= result.confidence <= 1.0

    def test_returns_reason(self):
        result = classify_query("What are the password requirements?")
        assert result.reason
        assert len(result.reason) > 10

    def test_off_topic_query_gets_low_confidence(self):
        """Off-topic queries should be classified with low confidence."""
        result = classify_query("What is the weather today?")
        assert result.confidence <= 0.3, \
            f"Off-topic query got high confidence: {result.confidence}"

    def test_empty_query_does_not_crash(self):
        """Empty or minimal queries should not raise exceptions."""
        result = classify_query("?")
        assert result.corpus in ["code", "compliance", "hybrid"]

    def test_very_long_query_does_not_crash(self):
        long_query = "password " * 100
        result = classify_query(long_query)
        assert result.corpus in ["code", "compliance", "hybrid"]
