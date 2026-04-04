"""
Stage 5.5 — Execution Test Harness.

MANDATORY testing framework to verify execution actually works.

Test cases:
1. OPEN_APP brave → verify process exists
2. SEARCH_WEB github → verify browser opened
3. MULTI_STEP open brave + search youtube → verify both steps

Usage:
    python -m agent.core.execution_test_harness

Or import and call:
    from agent.core.execution_test_harness import run_all_tests
    asyncio.run(run_all_tests())
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agent.core.execution_verifier import (
    verify_execution,
    verify_app_launched,
    verify_process_exists,
)
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# TEST CASE DEFINITION
# =============================================================================

@dataclass
class ExecutionTestCase:
    """A single execution test case."""
    name: str
    intent: str
    slots: Dict[str, Any]
    expect_success: bool = True
    verify_process: Optional[str] = None  # Process to verify
    description: str = ""


@dataclass
class TestResult:
    """Result of a test case."""
    test_name: str
    passed: bool
    execution_status: str
    verified: bool
    message: str
    duration: float
    details: Dict[str, Any]


# =============================================================================
# TEST CASES
# =============================================================================

EXECUTION_TEST_CASES = [
    # -------------------------------------------------------------------------
    # OPEN_APP Tests
    # -------------------------------------------------------------------------
    ExecutionTestCase(
        name="test_open_notepad",
        intent="OPEN_APP",
        slots={"app": "notepad"},
        expect_success=True,
        verify_process="notepad.exe",
        description="Open Notepad and verify process exists",
    ),
    
    ExecutionTestCase(
        name="test_open_calculator",
        intent="OPEN_APP",
        slots={"app": "calculator"},
        expect_success=True,
        verify_process="calc",
        description="Open Calculator and verify process exists",
    ),
    
    # Note: This test requires Brave browser installed
    ExecutionTestCase(
        name="test_open_brave",
        intent="OPEN_APP",
        slots={"app": "brave"},
        expect_success=True,
        verify_process="brave.exe",
        description="Open Brave browser and verify process exists",
    ),
    
    # -------------------------------------------------------------------------
    # SEARCH_WEB Tests
    # -------------------------------------------------------------------------
    ExecutionTestCase(
        name="test_search_web_github",
        intent="SEARCH_WEB",
        slots={"query": "github"},
        expect_success=True,
        description="Search for github and verify browser opened",
    ),
    
    # -------------------------------------------------------------------------
    # TYPE_TEXT Tests (Non-destructive)
    # -------------------------------------------------------------------------
    ExecutionTestCase(
        name="test_type_text",
        intent="TYPE_TEXT",
        slots={"text": "test"},
        expect_success=True,
        description="Type 'test' - verify keyboard action",
    ),
    
    # -------------------------------------------------------------------------
    # Multi-step Tests
    # -------------------------------------------------------------------------
    # Note: Multi-step tests require full pipeline
]


# =============================================================================
# TEST RUNNER
# =============================================================================

async def run_execution_test(
    test_case: ExecutionTestCase,
    executor_func=None,
) -> TestResult:
    """
    Run a single execution test.
    
    Args:
        test_case: The test case to run
        executor_func: Optional custom executor (for integration tests)
        
    Returns:
        TestResult with pass/fail status
    """
    print(f"\n{'='*60}")
    print(f"[TEST] {test_case.name}")
    print(f"[DESC] {test_case.description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # =====================================================================
        # STEP 1: Execute
        # =====================================================================
        print(f"\n[STEP 1] Executing: {test_case.intent}")
        print(f"[SLOTS] {test_case.slots}")
        
        if executor_func:
            # Use provided executor
            execution_result = await executor_func(test_case.intent, test_case.slots)
        else:
            # Use platform adapter directly
            from agent.platform.windows import WindowsAdapter
            adapter = WindowsAdapter()
            
            if test_case.intent == "OPEN_APP":
                execution_result = await adapter.open_app(test_case.slots.get("app", ""))
            elif test_case.intent == "SEARCH_WEB":
                execution_result = await adapter.search_web(test_case.slots.get("query", ""))
            elif test_case.intent == "TYPE_TEXT":
                execution_result = await adapter.type_text(test_case.slots.get("text", ""))
            elif test_case.intent == "PRESS_KEYS":
                execution_result = await adapter.press_keys(test_case.slots.get("keys", ""))
            elif test_case.intent == "OPEN_URL":
                execution_result = await adapter.open_url(test_case.slots.get("url", ""))
            else:
                execution_result = {"status": "error", "error": f"Unknown intent: {test_case.intent}"}
        
        execution_status = execution_result.get("status", "unknown")
        print(f"[EXECUTION RESULT] {execution_status}")
        
        # =====================================================================
        # STEP 2: Verify
        # =====================================================================
        print(f"\n[STEP 2] Verifying...")
        
        # Wait for action to complete
        await asyncio.sleep(2.0)
        
        verified, verify_msg = verify_execution(
            intent_type=test_case.intent,
            slots=test_case.slots,
            wait_time=5.0,
        )
        
        print(f"[VERIFICATION] {'✓ PASSED' if verified else '✗ FAILED'}")
        print(f"[MESSAGE] {verify_msg}")
        
        # =====================================================================
        # STEP 3: Check specific process if required
        # =====================================================================
        if test_case.verify_process:
            print(f"\n[STEP 3] Checking specific process: {test_case.verify_process}")
            proc_exists, proc_msg = verify_process_exists(test_case.verify_process)
            print(f"[PROCESS] {'✓ FOUND' if proc_exists else '✗ NOT FOUND'}")
            
            if not proc_exists and test_case.expect_success:
                verified = False
                verify_msg = f"Process {test_case.verify_process} not found"
        
        # =====================================================================
        # STEP 4: Determine pass/fail
        # =====================================================================
        duration = time.time() - start_time
        
        if test_case.expect_success:
            passed = execution_status == "success" and verified
        else:
            passed = execution_status != "success" or not verified
        
        print(f"\n[RESULT] {'✓ PASSED' if passed else '✗ FAILED'}")
        print(f"[DURATION] {duration:.2f}s")
        
        return TestResult(
            test_name=test_case.name,
            passed=passed,
            execution_status=execution_status,
            verified=verified,
            message=verify_msg,
            duration=duration,
            details={
                "execution_result": execution_result,
                "slots": test_case.slots,
            },
        )
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n[ERROR] {e}")
        
        return TestResult(
            test_name=test_case.name,
            passed=False,
            execution_status="error",
            verified=False,
            message=str(e),
            duration=duration,
            details={"error": str(e)},
        )


async def run_all_tests(
    test_cases: Optional[List[ExecutionTestCase]] = None,
    executor_func=None,
) -> List[TestResult]:
    """
    Run all execution tests.
    
    Args:
        test_cases: Optional list of test cases (defaults to EXECUTION_TEST_CASES)
        executor_func: Optional custom executor
        
    Returns:
        List of TestResult objects
    """
    if test_cases is None:
        test_cases = EXECUTION_TEST_CASES
    
    print("\n" + "="*70)
    print("       STAGE 5.5 EXECUTION TEST HARNESS")
    print("="*70)
    print(f"Running {len(test_cases)} test(s)...\n")
    
    results = []
    start_time = time.time()
    
    for test_case in test_cases:
        result = await run_execution_test(test_case, executor_func)
        results.append(result)
        
        # Brief pause between tests
        await asyncio.sleep(1.0)
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    total_time = time.time() - start_time
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    print("\n" + "="*70)
    print("       TEST SUMMARY")
    print("="*70)
    print(f"Total: {len(results)}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")
    print(f"Duration: {total_time:.2f}s")
    print()
    
    # Print failures
    if failed > 0:
        print("[FAILURES]")
        for r in results:
            if not r.passed:
                print(f"  ✗ {r.test_name}: {r.message}")
    
    print("="*70)
    
    return results


# =============================================================================
# QUICK TEST FUNCTIONS
# =============================================================================

async def test_open_app(app_name: str) -> TestResult:
    """Quick test: Open an app and verify."""
    test_case = ExecutionTestCase(
        name=f"test_open_{app_name}",
        intent="OPEN_APP",
        slots={"app": app_name},
        expect_success=True,
        description=f"Quick test: Open {app_name}",
    )
    return await run_execution_test(test_case)


async def test_search_web(query: str) -> TestResult:
    """Quick test: Search web and verify."""
    test_case = ExecutionTestCase(
        name=f"test_search_{query}",
        intent="SEARCH_WEB",
        slots={"query": query},
        expect_success=True,
        description=f"Quick test: Search for {query}",
    )
    return await run_execution_test(test_case)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stage 5.5 Execution Test Harness")
    parser.add_argument("--quick", action="store_true", help="Run quick test (notepad only)")
    parser.add_argument("--app", type=str, help="Test specific app")
    parser.add_argument("--search", type=str, help="Test specific search query")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(test_open_app("notepad"))
    elif args.app:
        asyncio.run(test_open_app(args.app))
    elif args.search:
        asyncio.run(test_search_web(args.search))
    elif args.all:
        asyncio.run(run_all_tests())
    else:
        # Default: run quick test
        print("Usage: python -m agent.core.execution_test_harness --all")
        print("       python -m agent.core.execution_test_harness --app notepad")
        print("       python -m agent.core.execution_test_harness --search github")
        print("\nRunning quick test (notepad)...")
        asyncio.run(test_open_app("notepad"))


if __name__ == "__main__":
    main()
