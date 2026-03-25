"""
FinOps Sentinel — Regression Test Suite
Run after every significant code change to catch regressions.

Usage:
    python tests/regression_test.py

Results are saved to evaluation/results/regression_YYYYMMDD_HHMM.json
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# ── TEST CASES ────────────────────────────────────────────────────────────────
# Format: (query, expected_corpus, min_confidence, must_contain_any)
# must_contain_any: answer must contain AT LEAST ONE of these terms (case-insensitive)
# Empty list = no content check

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
        ["cryptograph", "tls", "ssl", "strong", "open", "encrypt"],
    ),
    (
        "How often must vulnerability scans be performed?",
        "compliance", 0.85,
        ["three month", "quarterly", "every three", "12 month", "internal", "scan"],
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
        [],  # Any answer is acceptable — just shouldn't crash
    ),
    # Additional edge cases
    (
        "What are the physical security requirements for cardholder data?",
        "compliance", 0.85,
        ["physical", "access", "media", "secure"],
    ),
    (
        "How must Primary Account Numbers be stored?",
        "compliance", 0.85,
        ["pan", "account", "hash", "truncat", "encrypt", "render", "unreadable"],
    ),
]


def run_regression_tests() -> dict:
    """Run all regression tests and return results."""
    from agents.graph import build_graph

    print("Building agent graph...")
    graph = build_graph()

    results = []
    passed = 0
    failed = 0

    print(f"\nRunning {len(TEST_CASES)} regression tests...")
    print("=" * 65)

    for i, (query, expected_corpus, min_confidence, must_contain_any) in enumerate(TEST_CASES):
        print(f"\nTest {i+1}/{len(TEST_CASES)}: {query[:55]}...")

        try:
            result = graph.invoke({"query": query})
        except Exception as e:
            print(f"  Status:  ❌ CRASH — {e}")
            results.append({
                "query": query,
                "expected_corpus": expected_corpus,
                "actual_corpus": "error",
                "routing_pass": False,
                "confidence": 0.0,
                "confidence_pass": False,
                "content_pass": False,
                "missing_terms": [],
                "overall_pass": False,
                "error": str(e),
            })
            failed += 1
            continue

        actual_corpus = result.get("corpus", "unknown")
        actual_confidence = result.get("confidence", 0)
        answer = result.get("final_answer", "").lower()

        # Routing check
        routing_pass = actual_corpus == expected_corpus

        # Confidence check
        confidence_pass = actual_confidence >= min_confidence

        # Content check — ANY term must be present
        content_pass = True
        missing_terms = []
        if must_contain_any:
            found_any = any(term.lower() in answer for term in must_contain_any)
            if not found_any:
                content_pass = False
                missing_terms = must_contain_any

        overall_pass = routing_pass and confidence_pass and content_pass

        if overall_pass:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"

        print(f"  Status:     {status}")
        print(f"  Routing:    {actual_corpus} (expected: {expected_corpus}) {'✅' if routing_pass else '❌'}")
        print(f"  Confidence: {actual_confidence:.0%} (min: {min_confidence:.0%}) {'✅' if confidence_pass else '❌'}")
        if must_contain_any:
            print(f"  Content:    {'✅' if content_pass else f'❌ None of: {missing_terms[:3]}'}")

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

    # Print summary
    print("\n" + "=" * 65)
    print("REGRESSION TEST SUMMARY")
    print("=" * 65)
    print(f"Total:   {len(TEST_CASES)}")
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Score:   {passed}/{len(TEST_CASES)} ({passed/len(TEST_CASES)*100:.1f}%)")

    # Routing accuracy breakdown
    routing_results = [(r["expected_corpus"], r["routing_pass"]) for r in results]
    for corpus in ["compliance", "code", "hybrid"]:
        corpus_tests = [r for e, r in routing_results if e == corpus]
        if corpus_tests:
            pct = sum(corpus_tests) / len(corpus_tests) * 100
            print(f"Routing {corpus.upper()}: {sum(corpus_tests)}/{len(corpus_tests)} ({pct:.0f}%)")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(TEST_CASES),
        "passed": passed,
        "failed": failed,
        "score_pct": round(passed / len(TEST_CASES) * 100, 1),
        "tests": results,
    }

    output_path = (
        Path("evaluation/results")
        / f"regression_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    )
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved: {output_path}")
    return output


if __name__ == "__main__":
    run_regression_tests()
