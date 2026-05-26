"""
FinOps Sentinel - Query Classifier Node
Phase 3: Routes queries to CODE, COMPLIANCE, or HYBRID pipeline

Uses GPT-4o-mini with structured output to classify every query.
Evaluated on 50 labeled test queries — target accuracy >= 90%.
"""

import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from anthropic import Anthropic
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel

load_dotenv()

# ── OUTPUT SCHEMA ─────────────────────────────────────────────────────────────
class ClassificationResult(BaseModel):
    corpus: str       # "code", "compliance", or "hybrid"
    confidence: float # 0.0 - 1.0
    reason: str       # brief explanation of the routing decision


# ── CLASSIFIER PROMPT ─────────────────────────────────────────────────────────
CLASSIFIER_SYSTEM_PROMPT = """You are a query router for FinOps Sentinel.

Classify every query into exactly one of three categories:

CODE - Query is about source code, functions, architecture, technical implementation
Examples:
- "Which functions handle payment processing?"
- "Where is the authentication logic in the codebase?"
- "What does the order_service.py file do?"

COMPLIANCE - Query is about regulations, requirements, rules, standards
Examples:
- "What are the PCI-DSS password requirements?"
- "What does DORA require for incident reporting?"
- "What encryption standards does PCI-DSS mandate?"

HYBRID - Query spans both code AND compliance, requires both corpora
Examples:
- "Which of our functions need to change for PCI-DSS Requirement 3.4?"
- "Does our authentication code meet PCI-DSS password requirements?"
- "What code changes does DORA Article 9 require?"

IMPORTANT: If the query is completely unrelated to finance, compliance, or software
(e.g. weather, sports, cooking), classify it as COMPLIANCE with low confidence (0.1).
The system will handle out-of-scope queries gracefully.

Return JSON with fields:
- corpus: "code", "compliance", or "hybrid"
- confidence: float between 0.0 and 1.0
- reason: one sentence explaining the routing decision"""


# ── CLASSIFIER FUNCTION ───────────────────────────────────────────────────────
def classify_query(query: str) -> ClassificationResult:
    """
    Classify a query as code, compliance, or hybrid using Claude.

    Args:
        query: Natural language query from the user

    Returns:
        ClassificationResult with corpus, confidence, reason
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            system=CLASSIFIER_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Classify this query: {query}"}
            ],
        )

        import json
        result = json.loads(message.content[0].text)

        # Validate corpus value
        if result.get("corpus") not in ["code", "compliance", "hybrid"]:
            result["corpus"] = "compliance"  # safe default

        return ClassificationResult(**result)

    except Exception as e:
        logger.error(f"Classification failed: {e} — defaulting to compliance")
        return ClassificationResult(
            corpus="compliance",
            confidence=0.5,
            reason=f"Classification failed, defaulted to compliance: {e}",
        )


# ── LANGGRAPH NODE ────────────────────────────────────────────────────────────
def query_classifier_node(state: dict) -> dict:
    """
    LangGraph node: classifies query and sets corpus routing.

    Args:
        state: Current AgentState

    Returns:
        Updated state with corpus, confidence, routing_reason
    """
    query = state["query"]
    logger.info(f"Classifying query: '{query[:60]}...'")

    result = classify_query(query)

    logger.info(f"Routed to: {result.corpus} (confidence: {result.confidence:.2f})")
    logger.debug(f"Reason: {result.reason}")

    return {
        **state,
        "corpus": result.corpus,
        "confidence": result.confidence,
        "routing_reason": result.reason,
    }


# ── TEST ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_queries = [
        "What are the PCI-DSS password requirements?",
        "Which functions handle cardholder data in the codebase?",
        "Does our authentication code comply with PCI-DSS Requirement 8?",
        "What encryption does PCI-DSS mandate for stored data?",
        "Show me the payment processing functions",
    ]

    print("\nQuery Classification Test")
    print("=" * 60)
    for q in test_queries:
        result = classify_query(q)
        print(f"\nQuery:  {q}")
        print(f"Route:  {result.corpus.upper()} ({result.confidence:.0%})")
        print(f"Reason: {result.reason}")
