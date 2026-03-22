"""
FinOps Sentinel - Agent State Schema
Phase 3: Defines the data structure flowing through the LangGraph graph

Every node reads from and writes to this state object.
"""

from typing import TypedDict, Optional, Literal


class AgentState(TypedDict):
    """
    Shared state flowing through the entire LangGraph agent graph.

    Fields are populated progressively as the graph executes:
    - query: set by user, never changes
    - corpus: set by QueryClassifier
    - code_results: set by CodeAnalyzer (if CODE or HYBRID)
    - compliance_results: set by ComplianceMapper (if COMPLIANCE or HYBRID)
    - final_answer: set by the final synthesis step
    - sources: accumulated citations from all agents
    - confidence: overall confidence score
    - error: set if any node fails
    """

    # Input
    query: str

    # Routing decision
    corpus: Optional[Literal["code", "compliance", "hybrid"]]

    # Retrieval results
    code_results: Optional[list[dict]]
    compliance_results: Optional[list[dict]]

    # Generated outputs
    code_analysis: Optional[str]
    compliance_analysis: Optional[str]
    final_answer: Optional[str]

    # Metadata
    sources: Optional[list[dict]]
    confidence: Optional[float]
    routing_reason: Optional[str]
    error: Optional[str]