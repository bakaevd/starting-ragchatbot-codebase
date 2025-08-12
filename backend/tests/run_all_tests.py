#!/usr/bin/env python3
"""
Master test runner for the RAG chatbot system.
This script runs all tests and provides a comprehensive analysis of what's working and what's broken.
"""

import os
import sys
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


def run_all_tests():
    """Run all test suites and compile results"""
    print("=" * 70)
    print("RAG CHATBOT DIAGNOSTIC TEST SUITE")
    print("=" * 70)
    print()

    all_results = {}
    total_passed = 0
    total_failed = 0

    # Test 1: CourseSearchTool tests
    print("1. Testing CourseSearchTool functionality...")
    try:
        from test_course_search_tool import run_course_search_tool_tests

        passed, failed, failures = run_course_search_tool_tests()
        all_results["CourseSearchTool"] = {
            "passed": passed,
            "failed": failed,
            "failures": failures,
        }
        total_passed += passed
        total_failed += failed
    except Exception as e:
        print(f"Failed to run CourseSearchTool tests: {e}")
        all_results["CourseSearchTool"] = {"error": str(e)}
        total_failed += 1

    print("\n" + "-" * 50 + "\n")

    # Test 2: AIGenerator tests
    print("2. Testing AIGenerator functionality...")
    try:
        from test_ai_generator import run_ai_generator_tests

        passed, failed, failures = run_ai_generator_tests()
        all_results["AIGenerator"] = {
            "passed": passed,
            "failed": failed,
            "failures": failures,
        }
        total_passed += passed
        total_failed += failed
    except Exception as e:
        print(f"Failed to run AIGenerator tests: {e}")
        all_results["AIGenerator"] = {"error": str(e)}
        total_failed += 1

    print("\n" + "-" * 50 + "\n")

    # Test 3: RAG System tests
    print("3. Testing RAG System end-to-end functionality...")
    try:
        from test_rag_system import run_integration_tests, run_rag_system_tests

        rag_passed, rag_failed, rag_failures = run_rag_system_tests()
        print("\n" + "-" * 30)
        int_passed, int_failed, int_failures = run_integration_tests()

        all_results["RAGSystem"] = {
            "passed": rag_passed,
            "failed": rag_failed,
            "failures": rag_failures,
        }
        all_results["Integration"] = {
            "passed": int_passed,
            "failed": int_failed,
            "failures": int_failures,
        }
        total_passed += rag_passed + int_passed
        total_failed += rag_failed + int_failed
    except Exception as e:
        print(f"Failed to run RAG System tests: {e}")
        all_results["RAGSystem"] = {"error": str(e)}
        total_failed += 1

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    print(f"Total Tests: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(
        f"Success Rate: {total_passed/(total_passed+total_failed)*100:.1f}%"
        if total_passed + total_failed > 0
        else "N/A"
    )

    print("\nDETAILED RESULTS:")
    print("-" * 30)

    for test_suite, results in all_results.items():
        if "error" in results:
            print(f"{test_suite}: ERROR - {results['error']}")
        else:
            passed = results.get("passed", 0)
            failed = results.get("failed", 0)
            total_suite = passed + failed
            success_rate = passed / total_suite * 100 if total_suite > 0 else 0
            print(f"{test_suite}: {passed}/{total_suite} passed ({success_rate:.1f}%)")

    # Analyze and suggest fixes
    print("\n" + "=" * 70)
    print("DIAGNOSTIC ANALYSIS")
    print("=" * 70)

    analyze_test_results(all_results)

    return all_results


def analyze_test_results(results: Dict):
    """Analyze test results and suggest fixes"""

    print("\nISSUES IDENTIFIED:")
    print("-" * 20)

    issues_found = []

    # Check CourseSearchTool issues
    if "CourseSearchTool" in results:
        cst_results = results["CourseSearchTool"]
        if "error" in cst_results:
            issues_found.append("CourseSearchTool: Cannot load module - check imports")
        elif cst_results.get("failed", 0) > 0:
            issues_found.append("CourseSearchTool: execute() method has issues")
            for failure in cst_results.get("failures", []):
                print(f"  - {failure[0]}: {failure[1]}")

    # Check AIGenerator issues
    if "AIGenerator" in results:
        ai_results = results["AIGenerator"]
        if "error" in ai_results:
            issues_found.append("AIGenerator: Cannot load module - check imports")
        elif ai_results.get("failed", 0) > 0:
            issues_found.append("AIGenerator: Tool calling mechanism has issues")
            for failure in ai_results.get("failures", []):
                print(f"  - {failure[0]}: {failure[1]}")

    # Check Integration issues
    if "Integration" in results:
        int_results = results["Integration"]
        if int_results.get("failed", 0) > 0:
            for failure in int_results.get("failures", []):
                if "Config" in failure[0]:
                    issues_found.append(f"Configuration issue: {failure[1]}")
                elif "Module" in failure[0]:
                    issues_found.append(f"Module import issue: {failure[1]}")
                elif "SearchResults" in failure[0]:
                    issues_found.append(f"SearchResults class issue: {failure[1]}")

    # Check RAG System issues
    if "RAGSystem" in results:
        rag_results = results["RAGSystem"]
        if "error" in rag_results:
            issues_found.append("RAG System: Cannot initialize - check dependencies")
        elif rag_results.get("failed", 0) > 0:
            issues_found.append("RAG System: End-to-end flow has issues")

    if not issues_found:
        print("✓ No major issues detected in tests!")
        print("\nIf you're still getting 'query failed' errors, the issue might be:")
        print("1. Missing or invalid ANTHROPIC_API_KEY")
        print("2. No course documents loaded in /docs folder")
        print("3. ChromaDB database corruption")
        print("4. Network connectivity issues")
    else:
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. {issue}")

    print("\nRECOMMENDED FIXES:")
    print("-" * 20)

    # Generate specific fix recommendations
    fix_recommendations = generate_fix_recommendations(results)
    for i, fix in enumerate(fix_recommendations, 1):
        print(f"{i}. {fix}")

    print("\nNEXT STEPS:")
    print("-" * 12)
    print("1. Fix the highest priority issues first")
    print("2. Re-run this test suite after each fix")
    print(
        "3. Test with a real query: python -c \"from rag_system import RAGSystem; from config import config; rag = RAGSystem(config); print(rag.query('test'))\""
    )
    print("4. Check logs for additional error details")


def generate_fix_recommendations(results: Dict) -> List[str]:
    """Generate specific fix recommendations based on test results"""
    recommendations = []

    # Check for config issues
    if "Integration" in results:
        int_results = results["Integration"]
        for failure in int_results.get("failures", []):
            if "MAX_RESULTS is 0" in failure[1]:
                recommendations.append(
                    "CRITICAL: Fix config.py - set MAX_RESULTS to 5 instead of 0"
                )
            elif "Config missing attributes" in failure[1]:
                recommendations.append(
                    "Fix config.py - ensure all required attributes are present"
                )
            elif "ANTHROPIC_API_KEY" in failure[1]:
                recommendations.append("Set ANTHROPIC_API_KEY in ../.env file")

    # Check for module issues
    if any("error" in results.get(key, {}) for key in results):
        recommendations.append("Fix import issues - check Python path and dependencies")

    # Check for tool issues
    if (
        "CourseSearchTool" in results
        and results["CourseSearchTool"].get("failed", 0) > 0
    ):
        recommendations.append(
            "Debug CourseSearchTool.execute() - check vector store integration"
        )

    if "AIGenerator" in results and results["AIGenerator"].get("failed", 0) > 0:
        recommendations.append(
            "Debug AIGenerator tool calling - check Anthropic API integration"
        )

    # Default recommendations if no specific issues found
    if not recommendations:
        recommendations.extend(
            [
                "Check if ChromaDB has course data: look for files in backend/chroma_db/",
                "Verify course documents exist in ../docs/ folder",
                "Test vector store search directly",
                "Check application logs for runtime errors",
            ]
        )

    return recommendations


def test_real_system():
    """Test the real system with a simple query"""
    print("\n" + "=" * 70)
    print("TESTING REAL SYSTEM")
    print("=" * 70)

    try:
        # Try to import and test the real system
        from config import config
        from rag_system import RAGSystem

        print("Initializing RAG system...")
        rag = RAGSystem(config)

        print("Testing simple query...")
        response, sources = rag.query("What is machine learning?")

        print(f"Response received: {len(response)} characters")
        print(f"Sources returned: {len(sources)}")

        if "error" in response.lower() or "failed" in response.lower():
            print("❌ Real system test FAILED - query returned error")
            print(f"Response: {response[:200]}...")
        else:
            print("✅ Real system test PASSED - query completed successfully")
            print(f"Response preview: {response[:100]}...")

        return True

    except Exception as e:
        print(f"❌ Real system test FAILED with exception: {e}")
        return False


if __name__ == "__main__":
    # Run all tests
    results = run_all_tests()

    # Test real system
    test_real_system()

    print("\n" + "=" * 70)
    print("Testing complete! Review the analysis above to identify and fix issues.")
    print("=" * 70)
