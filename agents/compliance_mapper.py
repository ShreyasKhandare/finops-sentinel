"""
FinOps Sentinel - Compliance Mapper Agent Node
Phase 3: Retrieves and analyses compliance documents for a query

Uses hybrid retrieval + Cohere reranking (same as Phase 2)
Returns structured compliance analysis with citations.
"""

import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


# ── ANALYSIS PROMPT ───────────────────────────────────────────────────────────
COMPLIANCE_ANALYSIS_PROMPT = """You are a financial compliance analyst.

Analyse the provided compliance document excerpts and extract:
1. Specific requirements relevant to the query
2. Requirement numbers and article references
3. Exact page citations for every requirement
4. Key obligations (what MUST be done)

Rules:
- Only use information from the provided context
- Always include page numbers
- Be precise and structured
- Use requirement numbers when available (e.g. Requirement 8.3.6)

Format your response as:
REQUIREMENTS FOUND:
[bullet list of specific requirements with page citations]

KEY OBLIGATIONS:
[bullet list of what must be done]

SOURCES: Page X, Page Y, Page Z"""


# ── LANGGRAPH NODE ────────────────────────────────────────────────────────────
def compliance_mapper_node(state: dict) -> dict:
    """
    LangGraph node: retrieves compliance chunks and generates analysis.

    Args:
        state: Current AgentState with query

    Returns:
        Updated state with compliance_results and compliance_analysis
    """
    query = state["query"]
    logger.info(f"ComplianceMapper: processing '{query[:60]}...'")

    try:
        # Import here to avoid circular imports
        from ingestion.compliance_ingestor import get_chroma_collection
        from retrieval.hybrid_retriever import HybridRetrieverWithRerank

        collection = get_chroma_collection()
        retriever = HybridRetrieverWithRerank(collection)

        # Retrieve relevant compliance chunks
        results = retriever.search(query, n_results=5)
        logger.info(f"ComplianceMapper: retrieved {len(results)} chunks")

        if not results:
            return {
                **state,
                "compliance_results": [],
                "compliance_analysis": "No relevant compliance information found.",
            }

        # Build context
        context = "\n\n---\n\n".join([
            f"[Page {r['page']}]\n{r['text']}"
            for r in results[:5]
        ])

        # Generate analysis
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COMPLIANCE_ANALYSIS_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuery: {query}"},
            ],
            temperature=0.0,
            max_tokens=600,
        )

        analysis = response.choices[0].message.content
        logger.success(f"ComplianceMapper: analysis complete")

        return {
            **state,
            "compliance_results": results,
            "compliance_analysis": analysis,
            "sources": results,
        }

    except Exception as e:
        logger.error(f"ComplianceMapper failed: {e}")
        return {
            **state,
            "compliance_results": [],
            "compliance_analysis": f"Compliance analysis failed: {e}",
            "error": str(e),
        }