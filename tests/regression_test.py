"""
FinOps Sentinel — Regression Test Suite
Run after every significant code change to catch regressions.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# ── TEST CASES ────────────────────────────────────────────────────────────────
TEST_CASES = [
    (
        "What is the minimum password length required by PCI-DSS?",
        "compliance", 0.90,
        ["12", "password"],
    ),
    (
        "How long must audit logs be retained?",
        "compliance", 0.90,
        ["12", "month"],
    ),
    (
        "What encryption is required for cardholder data transmission?",
        "compliance", 0.85,
        ["cryptograph", "tls", "ssl", "strong", "open"],  # any of these
    ),
    (
        "How often must vulnerability scans be performed?",
        "compliance", 0.85,
        ["three month", "quarterly", "every three", "12 month", "internal"],
    ),
    (
        "What are the multi-factor authentication requirements?",
        "compliance", 0.85,
        ["factor", "authentication", "mfa", "two-factor", "require"],
    ),
    (
        "Which functions handle payment processing?",
        "code", 0.85,
        [],
    ),
    (
        "Does our authentication code meet PCI-DSS Requirement 8?",
        "hybrid", 0.85,
        [],
    ),
    (
        "What is the weather today?",
        "compliance", 0.0,
        ["cannot", "not contain", "insufficient", "does not"],
    ),
]


def run_regression_tests():
    """Run all regression tests and return results."""
    from agents.graph import build_graph

    print("Building agent graph...")
    graph = build_graph()

    results = []
    passed = 0
    failed = 0

    print(f"\nRunning {len(TEST_CASES)} regression tests...")
    print("=" * 60)

    for i, (query, expected_corpus, min_confidence, must_contain) in enumerate(TEST_CASES):
        print(f"\nTest {i+1}/{len(TEST_CASES)}: {query[:50]}...")

        result = graph.invoke({"query": query})

        actual_corpus = result.get("corpus", "unknown")
        actual_confidence = result.get("confidence", 0)
        answer = result.get("final_answer", "").lower()

        # Check routing
        routing_pass = actual_corpus == expected_corpus
        confidence_pass = actual_confidence >= min_confidence

        # Check answer contains expected terms
        content_pass = True
        missing_terms = []
        if must_contain:
            # Pass if ANY expected term is found
            found_any = any(term.lower() in answer for term in must_contain)
            if not found_any:
                content_pass = False
                missing_terms = must_contain

        overall_pass = routing_pass and confidence_pass and content_pass

        if overall_pass:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"

        print(f"  Status:     {status}")
        print(f"  Routing:    {actual_corpus} (expected {expected_corpus}) {'✅' if routing_pass else '❌'}")
        print(f"  Confidence: {actual_confidence:.0%} (min {min_confidence:.0%}) {'✅' if confidence_pass else '❌'}")
        if must_contain:
            print(f"  Content:    {'✅' if content_pass else f'❌ Missing: {missing_terms}'}")

        results.append({
            "query": query,
            "expected_corpus": expected_corpus,
            "actual_corpus": actual_corpus,
            "routing_pass": routing_pass,
            "confidence": actual_confidence,
            "confidence_pass": confidence_pass,
            "content_pass": content_pass,
            "missing_terms": missing_terms,
            "overall_pass": overall_pass,
        })

    # Summary
    print("\n" + "=" * 60)
    print(f"REGRESSION TEST RESULTS")
    print("=" * 60)
    print(f"Passed: {passed}/{len(TEST_CASES)}")
    print(f"Failed: {failed}/{len(TEST_CASES)}")
    print(f"Score:  {passed/len(TEST_CASES)*100:.0f}%")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "score_pct": round(passed/len(TEST_CASES)*100, 1),
        "tests": results,
    }

    output_path = Path("evaluation/results") / f"regression_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved: {output_path}")
    return output


if __name__ == "__main__":
    run_regression_tests()