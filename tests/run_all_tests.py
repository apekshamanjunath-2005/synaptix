"""
Synaptix Master Test Suite Runner
Executes comprehensive automated tests across all project milestones (1 through 8).
Generates an aggregated validation report.
"""

import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TEST_SUITES = [
    ("Milestone 1 — Foundation & Budget Guard", "tests/verify_milestone1_comprehensive.py"),
    ("Milestone 2 — Gemini Integration & RPM Burst Limiter", "tests/test_milestone2.py"),
    ("Milestone 3 — Google ADK Multi-Agent Orchestration", "tests/test_milestone3.py"),
    ("Milestone 4 — Firebase Firestore Tasks & Notes Layer", "tests/test_milestone4.py"),
    ("Milestone 5 — Google Calendar MCP Tool Provider", "tests/test_milestone5.py"),
    ("Milestone 6 — OpenWeatherMap Integration & Outdoor Engine", "tests/test_milestone6.py"),
    ("Milestone 7 — Smart Day Planner Multi-Agent Synthesis", "tests/test_milestone7.py"),
    ("Milestone 8 — UI & Glassmorphism Dashboard Experience", "tests/test_milestone8.py"),
    ("Gmail Agent — Human-in-the-Loop Email System", "tests/test_gmail_agent.py"),
    ("Multi-User OAuth — Google Login & Data Isolation", "tests/test_multi_user_oauth.py"),
    ("Smart Day Plans — Firestore Persistence & Isolation", "tests/test_day_plans.py"),
]


def run_master_test_suite():
    print("\n" + "█" * 70)
    print(" 🚀 SYNAPTIX MASTER VALIDATION SUITE: ALL MILESTONES + MULTI-USER OAUTH")
    print("█" * 70)

    import os
    python_executable = sys.executable
    results = []
    total_start = time.time()
    test_env = dict(os.environ)
    test_env["MOCK_MODE"] = "true"

    for title, test_script in TEST_SUITES:
        print(f"\n▶ Executing: {title} ({test_script})...")
        script_path = PROJECT_ROOT / test_script
        start_time = time.time()
        
        proc = subprocess.run(
            [python_executable, "-u", str(script_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            env=test_env
        )
        duration = round(time.time() - start_time, 2)
        
        if proc.returncode == 0:
            print(f"  ✅ {title}: PASSED ({duration}s)")
            results.append((title, "PASSED", duration, ""))
        else:
            print(f"  ❌ {title}: FAILED ({duration}s)")
            error_preview = proc.stderr[-400:] if proc.stderr else proc.stdout[-400:]
            print(f"     Error Output:\n{error_preview}")
            results.append((title, "FAILED", duration, error_preview))

    total_duration = round(time.time() - total_start, 2)

    print("\n" + "=" * 70)
    print(" 📊 SYNAPTIX TEST EXECUTION SUMMARY")
    print("=" * 70)
    passed_count = sum(1 for _, status, _, _ in results if status == "PASSED")
    total_count = len(results)

    for title, status, duration, _ in results:
        status_icon = "✅" if status == "PASSED" else "❌"
        print(f"  {status_icon} [{status}] {title} ({duration}s)")

    print("-" * 70)
    print(f"  Total Suites: {total_count} | Passed: {passed_count} | Failed: {total_count - passed_count}")
    print(f"  Total Verification Time: {total_duration}s")
    print("=" * 70)

    if passed_count == total_count:
        print(" 🎉 ALL MILESTONE TEST SUITES PASSED WITH 100% SUCCESS!\n")
        return 0
    else:
        print(" ⚠️ SOME TEST SUITES FAILED. PLEASE REVIEW LOGS ABOVE.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_master_test_suite())
