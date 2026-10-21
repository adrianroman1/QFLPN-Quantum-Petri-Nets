#!/usr/bin/env bash
#
# P2-BENCH-CONFIG-01
# Complete audit orchestrator.
#
# Exit codes:
#   0 = all technical gates passed; acceptance is NOT granted
#   1 = one or more gates failed or evidence is missing
#   2 = execution environment/repository error
#
# This script does not modify production source files or GitHub.

set -uo pipefail

EXPECTED_TEST_COUNT=29

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: Not inside a Git repository."
    exit 2
}

cd "$ROOT"

mkdir -p audit

echo
echo "=================================================="
echo " P2-BENCH-CONFIG-01 AUDIT"
echo "=================================================="

# --------------------------------------------------
# STEP 01 - SHA verification
# --------------------------------------------------

echo
echo "[01/07] GIT SHA AND SHA-256 VERIFICATION"

bash audit/verify_original_sha.sh
SHA_STATUS=$?

# --------------------------------------------------
# STEP 02 - Function review
# --------------------------------------------------

echo
echo "[02/07] FUNCTION BODY / SIGNATURE / DECORATOR REVIEW"

python audit/compare_function_bodies.py \
    audit/validate_benchmark.original.py \
    P2/benchmarks/validate_benchmark.py

FUNCTION_STATUS=$?

# --------------------------------------------------
# STEP 03 - Contract integration
# --------------------------------------------------

echo
echo "[03/07] CONTRACT AST REVIEW"

python audit/verify_contract_integration.py

CONTRACT_STATUS=$?

# --------------------------------------------------
# STEP 04 - Compilation
# --------------------------------------------------

echo
echo "[04/07] PYTHON COMPILATION"

python -m py_compile \
    P2/benchmarks/benchmark_contract.py \
    P2/benchmarks/benchmark_runner.py \
    P2/benchmarks/validate_benchmark.py

COMPILE_STATUS=$?

python - "$COMPILE_STATUS" <<'PY'
import json
import sys
from pathlib import Path

status = int(sys.argv[1])

report = {
    "executed": True,
    "passed": status == 0,
    "exit_code": status,
}

Path("audit/compile_report.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
PY

# --------------------------------------------------
# STEP 05 - Behavioral equivalence
# --------------------------------------------------

echo
echo "[05/07] BEHAVIORAL EQUIVALENCE"

python audit/behavior_equivalence.py

BEHAVIOR_STATUS=$?

# --------------------------------------------------
# STEP 06 - Existing tests
# --------------------------------------------------

echo
echo "[06/07] EXISTING BENCHMARK TESTS"

pytest P2/tests/test_benchmark.py -q \
    > audit/pytest_output.txt 2>&1

TEST_STATUS=$?

cat audit/pytest_output.txt

python - "$TEST_STATUS" "$EXPECTED_TEST_COUNT" <<'PY'
import json
import re
import sys
from pathlib import Path

exit_code = int(sys.argv[1])
expected = int(sys.argv[2])

output_path = Path("audit/pytest_output.txt")

output = (
    output_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    if output_path.exists()
    else ""
)

passed_match = re.search(
    r"(\d+)\s+passed\b",
    output,
)

failed_match = re.search(
    r"(\d+)\s+failed\b",
    output,
)

error_match = re.search(
    r"(\d+)\s+errors?\b",
    output,
)

passed = (
    int(passed_match.group(1))
    if passed_match
    else 0
)

failed = (
    int(failed_match.group(1))
    if failed_match
    else 0
)

errors = (
    int(error_match.group(1))
    if error_match
    else 0
)

report = {
    "executed": True,
    "exit_code": exit_code,
    "passed": passed,
    "failed": failed,
    "errors": errors,
    "expected_passed": expected,
    "passed_all_expected": (
        exit_code == 0
        and passed == expected
        and failed == 0
        and errors == 0
    ),
    "output_file": "audit/pytest_output.txt",
}

Path("audit/tests_report.json").write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)
PY

# --------------------------------------------------
# STEP 07 - CI evidence
# --------------------------------------------------

echo
echo "[07/07] CI EVIDENCE"

echo "Checking audit/ci_status.json."

# --------------------------------------------------
# FINAL REPORT
# --------------------------------------------------

echo
echo "=================================================="
echo " GENERATING FINAL AUDIT REPORT"
echo "=================================================="

python <<'PY'
import json
import subprocess
from pathlib import Path


def read_json(path):
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (
        OSError,
        subprocess.CalledProcessError,
    ):
        return None


sha = read_json("audit/sha_report.json")
functions = read_json("audit/function_comparison.json")
contract = read_json("audit/contract_report.json")
behavior = read_json("audit/behavior_report.json")
compile_report = read_json("audit/compile_report.json")
tests = read_json("audit/tests_report.json")
ci = read_json("audit/ci_status.json")

head = git_head()

sha_ok = bool(
    sha
    and sha.get("passed") is True
    and sha.get("git_identity_pass") is True
    and sha.get("original_sha256")
    and sha.get("migrated_sha256")
)

function_counts = (
    functions.get("counts", {})
    if functions
    else {}
)

function_ok = bool(
    functions
    and functions.get("passed") is True
    and function_counts.get("missing") == 0
    and function_counts.get("added") == 0
    and function_counts.get("identical") == 12
    and function_counts.get("changed") == 3
    and function_counts.get("unexpected_changes") == 0
    and function_counts.get("signature_changes") == 0
    and function_counts.get("decorator_changes") == 0
)

contract_checks = (
    contract.get("checks", {})
    if contract
    else {}
)

contract_ok = bool(
    contract
    and contract.get("passed") is True
    and contract_checks
    and all(
        value is True
        for value in contract_checks.values()
    )
)

behavior_ok = bool(
    behavior
    and behavior.get("passed") is True
    and behavior.get("equivalent") is True
    and behavior.get("original_verdict")
        == behavior.get("migrated_verdict")
    and behavior.get("error_diff") == []
    and behavior.get("original_error_count")
        == behavior.get("migrated_error_count")
    and behavior.get("artifact_hashes")
)

compile_ok = bool(
    compile_report
    and compile_report.get("executed") is True
    and compile_report.get("passed") is True
)

tests_ok = bool(
    tests
    and tests.get("passed_all_expected") is True
    and tests.get("passed") == 29
    and tests.get("failed") == 0
    and tests.get("errors") == 0
)

ci_ok = bool(
    ci
    and ci.get("executed") is True
    and ci.get("conclusion") == "success"
    and ci.get("head_sha") == head
    and isinstance(ci.get("run_url"), str)
    and ci.get("run_url").startswith("https://")
    and isinstance(ci.get("completed_at"), str)
    and bool(ci.get("completed_at").strip())
)

checks = {
    "sha": sha_ok,
    "function_review": function_ok,
    "contract_review": contract_ok,
    "behavior_review": behavior_ok,
    "compile": compile_ok,
    "tests": tests_ok,
    "ci": ci_ok,
}

ready = all(checks.values())

report = {
    "defect_id": "P2-BENCH-CONFIG-01",

    "repository_head": head,

    "original_git_sha": (
        sha.get("expected_original_git_sha")
        if sha else None
    ),

    "original_sha256": (
        sha.get("original_sha256")
        if sha else None
    ),

    "migrated_sha256": (
        sha.get("migrated_sha256")
        if sha else None
    ),

    "function_review": {
        "missing": function_counts.get("missing"),
        "added": function_counts.get("added"),
        "identical": function_counts.get("identical"),
        "changed": function_counts.get("changed"),
        "unexpected": function_counts.get(
            "unexpected_changes"
        ),
        "signature_changes": function_counts.get(
            "signature_changes"
        ),
        "decorator_changes": function_counts.get(
            "decorator_changes"
        ),
    },

    "contract_review": {
        "artifact_paths": contract_checks.get(
            "validate_results_uses_contract_artifact_paths"
        ),
        "artifacts": contract_checks.get(
            "validate_markdown_uses_contract_artifacts"
        ),
        "cli_results_check": contract_checks.get(
            "assertion_uses_args_results"
        ),
        "config_loader": contract_checks.get(
            "loader_uses_args_config"
        ),
    },

    "behavior_review": {
        "equivalent": (
            behavior.get("equivalent")
            if behavior else None
        ),
        "original_verdict": (
            behavior.get("original_verdict")
            if behavior else None
        ),
        "migrated_verdict": (
            behavior.get("migrated_verdict")
            if behavior else None
        ),
        "original_error_count": (
            behavior.get("original_error_count")
            if behavior else None
        ),
        "migrated_error_count": (
            behavior.get("migrated_error_count")
            if behavior else None
        ),
        "error_diff": (
            behavior.get("error_diff")
            if behavior else None
        ),
        "artifact_hashes": (
            behavior.get("artifact_hashes")
            if behavior else None
        ),
    },

    "compile": compile_ok,

    "tests": {
        "passed": tests.get("passed") if tests else None,
        "failed": tests.get("failed") if tests else None,
        "errors": tests.get("errors") if tests else None,
    },

    "ci": {
        "executed": bool(
            ci and ci.get("executed") is True
        ),
        "conclusion": (
            ci.get("conclusion")
            if ci else None
        ),
        "head_sha": (
            ci.get("head_sha")
            if ci else None
        ),
        "matches_current_head": bool(
            ci and ci.get("head_sha") == head
        ),
        "run_url": (
            ci.get("run_url")
            if ci else None
        ),
    },

    "checks": checks,

    "readiness": (
        "READY_FOR_VALIDATION"
        if ready
        else "NOT_READY"
    ),

    "acceptance": False,

    "acceptance_status": "NOT_GRANTED",
}

Path("audit/final_audit_report.json").write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )
)

print()
print("AUDIT COMPLETE")

print(
    "READINESS:",
    report["readiness"],
)

print("ACCEPTANCE: NOT GRANTED")

raise SystemExit(0 if ready else 1)
PY

FINAL_STATUS=$?

if [[ "$FINAL_STATUS" -ne 0 ]]; then
    echo
    echo "AUDIT COMPLETE - NOT READY"
    echo "See audit/final_audit_report.json"
    echo "Acceptance: NOT GRANTED"
    exit 1
fi

echo
echo "AUDIT COMPLETE - READY FOR VALIDATION"
echo "See audit/final_audit_report.json"
echo "Acceptance: NOT GRANTED"

exit 0
