"""
FinOps Sentinel - LangGraph Agent Graph
Phase 3: Main orchestration graph

Graph structure:
    query_classifier
         |
         |-- compliance --> compliance_mapper --> format_response
         |-- code -------> compliance_mapper --> format_response  (Phase 3 fallback)
         |-- hybrid -----> compliance_mapper --> format_response  (Phase 3 fallback)

Note: Code analyzer uses compliance mapper as fallback in Phase 3.
Full code corpus added in Phase 4 when we have the code ingestion pipeline.
"""

import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from agents.state import AgentState
from agents.query_classifier import query_classifier_node
from agents.compliance_mapper import compliance_mapper_node


# ── ROUTING FUNCTION ──────────────────────────────────────────────────────────
def route_query(state: AgentState) -> str:
    """
    Conditional edge function — decides which node to go to after classifier.

    Args:
        state: Current AgentState with corpus field set

    Returns:
        Node name to route to
    """
    corpus = state.get("corpus", "compliance")
    logger.debug(f"Routing to: {corpus}")

    if corpus == "compliance":
        return "compliance_mapper"
    elif corpus == "code":
        # Phase 3: code queries routed to compliance mapper as fallback
        # Phase 4: will route to code_analyzer node
        return "compliance_mapper"
    elif corpus == "hybrid":
        return "compliance_mapper"
    else:
        return "compliance_mapper"


# ── FORMAT RESPONSE NODE ──────────────────────────────────────────────────────
def format_response_node(state: AgentState) -> AgentState:
    """
    Final node: formats the agent outputs into a clean final answer.

    Args:
        state: Current AgentState with analysis fields populated

    Returns:
        Updated state with final_answer set
    """
    corpus = state.get("corpus", "compliance")
    compliance_analysis = state.get("compliance_analysis", "")
    routing_reason = state.get("routing_reason", "")
    query = state.get("query", "")

    # Build final answer
    answer_parts = []

    if compliance_analysis:
        answer_parts.append(compliance_analysis)

    if not answer_parts:
        final_answer = (
            "I could not find sufficient information to answer this query. "
            "Please try rephrasing or consult the source documents directly."
        )
    else:
        final_answer = "\n\n".join(answer_parts)

    logger.success(f"Graph complete — corpus: {corpus}")

    return {
        **state,
        "final_answer": final_answer,
    }


# ── BUILD GRAPH ───────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    """
    Build and compile the LangGraph agent graph.

    Returns:
        Compiled LangGraph application
    """
    # Create graph with state schema
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("query_classifier", query_classifier_node)
    graph.add_node("compliance_mapper", compliance_mapper_node)
    graph.add_node("format_response", format_response_node)

    # Set entry point
    graph.set_entry_point("query_classifier")

    # Add conditional routing after classifier
    graph.add_conditional_edges(
        "query_classifier",
        route_query,
        {
            "compliance_mapper": "compliance_mapper",
        },
    )

    # Linear edges after routing
    graph.add_edge("compliance_mapper", "format_response")
    graph.add_edge("format_response", END)

    # Compile
    app = graph.compile()
    logger.info("LangGraph agent graph compiled successfully")

    return app


# ── SINGLETON ─────────────────────────────────────────────────────────────────
_graph_instance = None

def get_graph():
    """Get or create the compiled graph (singleton pattern)."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Building LangGraph agent graph...")
    app = build_graph()

    # Test queries
    test_queries = [
        "What are the PCI-DSS password requirements?",
        "What encryption is required for cardholder data at rest?",
        "What are the logging requirements under PCI-DSS?",
    ]

    print("\nRunning test queries through agent graph...")
    print("=" * 60)

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        result = app.invoke({"query": query})

        print(f"Corpus routed to: {result['corpus'].upper()}")
        print(f"Routing reason: {result['routing_reason']}")
        print(f"\nAnswer:\n{result['final_answer'][:500]}...")
        print("=" * 60)