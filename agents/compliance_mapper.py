"""
FinOps Sentinel - Compliance Mapper Agent Node
Phase 3: Retrieves and analyses compliance documents for a query
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
    """
    query = state["query"]
    logger.info(f"ComplianceMapper: processing '{query[:60]}...'")

    try:
        from ingestion.compliance_ingestor import get_chroma_collection
        from retrieval.hybrid_retriever import HybridRetrieverWithRerank

        collection = get_chroma_collection()
        retriever = HybridRetrieverWithRerank(collection)

        # Retrieve relevant compliance chunks
        results = retriever.search(query, n_results=5)
        logger.info(f"ComplianceMapper: retrieved {len(results)} chunks")

        # Safety — ensure all results have required fields
        safe_results = []
        for r in results:
            safe_r = {
                "text": r.get("text", ""),
                "source": r.get("source", "unknown"),
                "page": r.get("page", 0),
                "distance": float(r.get("distance", 0.5)),
            }
            if safe_r["text"]:  # only include non-empty chunks
                safe_results.append(safe_r)

        if not safe_results:
            logger.warning("ComplianceMapper: no valid results found")
            return {
                **state,
                "compliance_results": [],
                "compliance_analysis": (
                    "No relevant compliance information found for this query. "
                    "Please try rephrasing or ask about a specific PCI-DSS requirement."
                ),
            }

        # Build context from safe results
        context = "\n\n---\n\n".join([
            f"[Page {r['page']}]\n{r['text']}"
            for r in safe_results[:5]
        ])

        # Generate analysis
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COMPLIANCE_ANALYSIS_PROMPT},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuery: {query}",
                },
            ],
            temperature=0.0,
            max_tokens=600,
        )

        analysis = response.choices[0].message.content
        logger.success("ComplianceMapper: analysis complete")

        return {
            **state,
            "compliance_results": safe_results,
            "compliance_analysis": analysis,
            "sources": safe_results,
        }

    except Exception as e:
        logger.error(f"ComplianceMapper failed: {e}")
        return {
            **state,
            "compliance_results": [],
            "compliance_analysis": f"Compliance analysis failed: {e}",
            "error": str(e),
        }