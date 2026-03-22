"""
FinOps Sentinel — RAGAS Evaluation Suite
Phase 2: Establish baseline metrics before hybrid retrieval

Metrics measured:
- Faithfulness: does answer only use retrieved context?
- Answer Relevancy: does answer address the question?
- Context Precision: are retrieved chunks relevant?
- Context Recall: did we retrieve all relevant chunks?
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from loguru import logger
import os

load_dotenv()

from ingestion.compliance_ingestor import get_chroma_collection, query_compliance

# ── CONFIG ────────────────────────────────────────────────────────────────────
RESULTS_PATH = Path("evaluation/results")
RESULTS_PATH.mkdir(exist_ok=True)

# ── EVALUATION DATASET ───────────────────────────────────────────────────────
# Hand-crafted Q&A pairs grounded in PCI-DSS v4.0.1
# ground_truth = the correct answer we expect the system to find
EVAL_QUESTIONS = [
    {
        "question": "What are the requirements for protecting cardholder data at rest?",
        "ground_truth": "Cardholder data at rest must be protected through data retention policies, rendering PAN unreadable using strong cryptography, and secure deletion when no longer needed. Sensitive Authentication Data must not be stored after authorization. Physical media must be securely stored and destroyed when no longer needed."
    },
    {
        "question": "What are the password and authentication requirements in PCI-DSS?",
        "ground_truth": "PCI-DSS requires passwords to be at least 12 characters, contain both numeric and alphabetic characters, and be changed every 90 days. Accounts must be locked after no more than 10 failed attempts. Multi-factor authentication is required for all non-console administrative access."
    },
    {
        "question": "What encryption is required for data transmission?",
        "ground_truth": "Strong cryptography must be used to safeguard PAN during transmission over open public networks. Trusted keys and certificates must be used, and wireless networks transmitting cardholder data must use strong encryption such as WPA3."
    },
    {
        "question": "What are the logging and audit trail requirements?",
        "ground_truth": "Audit logs must capture all individual user access to cardholder data, all actions taken by root or administrative privileges, access to audit trails, invalid logical access attempts, and changes to authentication mechanisms. Logs must be retained for at least 12 months with 3 months immediately available."
    },
    {
        "question": "What vulnerability scanning requirements does PCI-DSS mandate?",
        "ground_truth": "Internal and external vulnerability scans must be performed at least once every three months. External scans must be performed by a PCI SSC Approved Scanning Vendor. High-risk and critical vulnerabilities must be resolved and rescanned. Penetration testing must be performed at least once every 12 months."
    },
    {
        "question": "What are the requirements for network security controls?",
        "ground_truth": "Network security controls must restrict inbound and outbound traffic to only that which is necessary. All connections into the cardholder data environment must go through a firewall or router. Direct public access between the internet and cardholder data environment is prohibited."
    },
    {
        "question": "How must access to cardholder data be controlled?",
        "ground_truth": "Access to system components and cardholder data must be limited to only those individuals whose job requires such access. Access control systems must deny all access by default. Unique IDs must be assigned to each person with computer access."
    },
    {
        "question": "What are the requirements for protecting stored account data?",
        "ground_truth": "Primary Account Numbers must be rendered unreadable anywhere they are stored using strong one-way hash functions, truncation, index tokens, or strong cryptography. Full PAN must not be stored in logs, databases, or files unless protected."
    },
]


# ── LLM ANSWER GENERATION ────────────────────────────────────────────────────
def generate_answer(question: str, contexts: list[str]) -> str:
    """
    Generate an answer using GPT-4o-mini given question and retrieved contexts.

    Args:
        question: The compliance question
        contexts: List of retrieved chunk texts

    Returns:
        Generated answer string
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    context_text = "\n\n---\n\n".join(contexts[:5])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a financial compliance expert. "
                    "Answer based ONLY on the provided context. "
                    "If the answer is not in the context, say 'I cannot find this information.'"
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion: {question}"
            }
        ],
        temperature=0.0,
        max_tokens=400,
    )
    return response.choices[0].message.content


# ── MAIN EVALUATION ───────────────────────────────────────────────────────────
def run_evaluation(phase_label: str = "phase2_baseline") -> dict:
    """
    Run full RAGAS evaluation on the compliance corpus.

    Args:
        phase_label: Label for this evaluation run (used in output filename)

    Returns:
        Dict of metric scores
    """
    logger.info(f"Starting RAGAS evaluation — {phase_label}")
    logger.info(f"Evaluating {len(EVAL_QUESTIONS)} questions")
    logger.info("=" * 50)

    collection = get_chroma_collection()

    # Build evaluation dataset
    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for i, item in enumerate(EVAL_QUESTIONS):
        logger.info(f"Processing question {i+1}/{len(EVAL_QUESTIONS)}: {item['question'][:60]}...")

        # NEW — hybrid + reranking
        from retrieval.hybrid_retriever import HybridRetrieverWithRerank
        if 'hybrid_retriever' not in dir():
            hybrid_retriever = HybridRetrieverWithRerank(collection)
        results = hybrid_retriever.search(item["question"], n_results=5)
        retrieved_contexts = [r["text"] for r in results]

        # Generate answer
        answer = generate_answer(item["question"], retrieved_contexts)

        questions.append(item["question"])
        answers.append(answer)
        contexts.append(retrieved_contexts)
        ground_truths.append(item["ground_truth"])

        logger.debug(f"  Retrieved {len(retrieved_contexts)} chunks")
        logger.debug(f"  Answer length: {len(answer)} chars")

    # Build RAGAS dataset
    eval_dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })

    logger.info("Running RAGAS metrics...")

    # Configure LLM for RAGAS
    ragas_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    ragas_embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Run evaluation
    results = evaluate(
        dataset=eval_dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    # Extract scores
    def extract_score(val) -> float:
        """Handle RAGAS returning either a float or a list."""
        if isinstance(val, list):
            valid = [v for v in val if v is not None]
            return round(float(sum(valid) / len(valid)), 4) if valid else 0.0
        return round(float(val), 4)

    scores = {
        "phase": phase_label,
        "timestamp": datetime.now().isoformat(),
        "num_questions": len(EVAL_QUESTIONS),
        "faithfulness": extract_score(results["faithfulness"]),
        "answer_relevancy": extract_score(results["answer_relevancy"]),
        "context_precision": extract_score(results["context_precision"]),
        "context_recall": extract_score(results["context_recall"]),
    }

    # Save results
    output_path = RESULTS_PATH / f"{phase_label}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_path, "w") as f:
        json.dump(scores, f, indent=2)

    # Print results
    logger.success("=" * 50)
    logger.success("RAGAS EVALUATION RESULTS")
    logger.success("=" * 50)
    print(f"\n{'Metric':<25} {'Score':<10} {'Target':<10} {'Status'}")
    print("-" * 60)
    targets = {
        "faithfulness": 0.88,
        "answer_relevancy": 0.84,
        "context_precision": 0.80,
        "context_recall": 0.75,
    }
    for metric, target in targets.items():
        score = scores[metric]
        status = "✅ PASS" if score >= target else "❌ BELOW TARGET"
        print(f"{metric:<25} {score:<10} {target:<10} {status}")

    print(f"\nResults saved to: {output_path}")
    return scores


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scores = run_evaluation("phase2_hybrid_rerank")
    print("\nPhase 1 baseline established. Run again after Phase 2")
    print("improvements to measure the delta.")