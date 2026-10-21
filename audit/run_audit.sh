#!/usr/bin/env bash
#
# P2-BENCH-CONFIG-01
# Consolidated Audit Orchestrator
#
# Execută:
# 1. Source integrity
# 2. Contract integration
# 3. Function / AST equivalence
# 4. Behavioral preservation
# 5. Python compilation
# 6. Pytest
# 7. GitHub Actions verification
#
# Generează:
# audit/audit_report.json
#
# Nu modifică automat sursele proiectului.
#

set -uo pipefail


# =========================================================
# CONFIGURATION
# =========================================================

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: Repository Git not found." >&2
    exit 2
}

cd "$ROOT" || exit 2

PYTHON="${PYTHON:-python3}"

AUDIT_DIR="$ROOT/audit"

REPORT="$AUDIT_DIR/audit_report.json"

mkdir -p "$AUDIT_DIR"


# =========================================================
# TEMPORARY LOG DIRECTORY
# =========================================================

LOG_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$LOG_DIR"
}

trap cleanup EXIT


# =========================================================
# EXECUTION STATUS
# =========================================================

SOURCE_STATUS="NOT RUN"

CONTRACT_STATUS="NOT RUN"

FUNCTION_STATUS="NOT RUN"

BEHAVIOR_STATUS="NOT RUN"

COMPILE_STATUS="NOT RUN"

PYTEST_STATUS="NOT RUN"

CI_STATUS="NOT VERIFIED"

PYTEST_COLLECTED=0

PYTEST_PASSED=0

PYTEST_FAILED=0

CI_RUN_ID=""

CI_WORKFLOW="p2-validation.yml"


# =========================================================
# HELPER: RUN AUDIT STAGE
# =========================================================

run_stage() {

    local name="$1"

    shift

    local log_file="$LOG_DIR/${name}.log"

    echo
    echo "=================================================="
    echo "RUNNING: $name"
    echo "=================================================="

    if "$@" >"$log_file" 2>&1; then

        echo "STATUS: PASS"

        cat "$log_file"

        printf "PASS"

    else

        local exit_code=$?

        echo "STATUS: FAIL"
        echo "Exit code: $exit_code"

        cat "$log_file"

        printf "FAIL"
    }
}


# =========================================================
# 1. SOURCE INTEGRITY
# =========================================================

SOURCE_STATUS="$(
    run_stage \
        source_integrity \
        bash audit/verify_original_sha.sh
)"


# =========================================================
# 2. CONTRACT INTEGRATION
# =========================================================

CONTRACT_STATUS="$(
    run_stage \
        contract_integration \
        "$PYTHON" \
        audit/verify_contract_integration.py
)"


# =========================================================
# 3. FUNCTION / AST EQUIVALENCE
# =========================================================

FUNCTION_STATUS="$(
    run_stage \
        function_equivalence \
        "$PYTHON" \
        audit/compare_function_bodies.py
)"


# =========================================================
# 4. BEHAVIORAL PRESERVATION
# =========================================================

BEHAVIOR_STATUS="$(
    run_stage \
        behavior_equivalence \
        "$PYTHON" \
        audit/behavior_equivalence.py
)"


# =========================================================
# 5. PYTHON COMPILATION
# =========================================================

COMPILE_FILES=(

    P2/benchmarks/benchmark_contract.py

    P2/benchmarks/benchmark_runner.py

    P2/benchmarks/validate_benchmark.py

    P2/tests/test_benchmark.py

    audit/verify_contract_integration.py

    audit/compare_function_bodies.py

    audit/behavior_equivalence.py
)

if "$PYTHON" -m py_compile "${COMPILE_FILES[@]}" \
    >"$LOG_DIR/py_compile.log" 2>&1; then

    COMPILE_STATUS="PASS"

else

    COMPILE_STATUS="FAIL"

fi

echo
echo "PY_COMPILE: $COMPILE_STATUS"

cat "$LOG_DIR/py_compile.log"


# =========================================================
# 6. PYTEST
# =========================================================

if command -v pytest >/dev/null 2>&1; then

    PYTEST_LOG="$LOG_DIR/pytest.log"

    if pytest -q P2/tests/test_benchmark.py \
        >"$PYTEST_LOG" 2>&1; then

        PYTEST_STATUS="PASS"

    else

        PYTEST_STATUS="FAIL"

    fi

    cat "$PYTEST_LOG"

    # -----------------------------------------------------
    # Extract test counts from pytest output
    # -----------------------------------------------------

    COUNTS="$(
        "$PYTHON" - "$PYTEST_LOG" <<'PY'
import re
import sys

content = open(
    sys.argv[1],
    encoding="utf-8",
    errors="replace",
).read()

passed = 0
failed = 0
errors = 0
skipped = 0

patterns = {
    "passed": r"(\d+)\s+passed",
    "failed": r"(\d+)\s+failed",
    "errors": r"(\d+)\s+errors?",
    "skipped": r"(\d+)\s+skipped",
}

for key, pattern in patterns.items():

    match = re.search(pattern, content)

    if match:

        value = int(match.group(1))

        if key == "passed":
            passed = value

        elif key == "failed":
            failed = value

        elif key == "errors":
            errors = value

        elif key == "skipped":
            skipped = value

print(
    passed,
    failed,
    errors,
    skipped,
)
PY
    )"

    read -r \
        PYTEST_PASSED \
        PYTEST_FAILED \
        PYTEST_ERRORS \
        PYTEST_SKIPPED \
        <<< "$COUNTS"

    PYTEST_COLLECTED=$(
        (
            PYTEST_PASSED
            + PYTEST_FAILED
            + PYTEST_ERRORS
            + PYTEST_SKIPPED
        )
    )

else

    PYTEST_STATUS="NOT VERIFIED"

    PYTEST_ERRORS=0

    PYTEST_SKIPPED=0

fi

echo
echo "PYTEST STATUS: $PYTEST_STATUS"

echo "Collected: $PYTEST_COLLECTED"

echo "Passed: $PYTEST_PASSED"

echo "Failed: $PYTEST_FAILED"

echo "Errors: $PYTEST_ERRORS"

echo "Skipped: $PYTEST_SKIPPED"


# =========================================================
# 7. GITHUB ACTIONS
# =========================================================

COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"

BRANCH="$(git branch --show-current 2>/dev/null || true)"

if command -v gh >/dev/null 2>&1 && [ -n "$COMMIT" ]; then

    CI_LOG="$LOG_DIR/ci_runs.json"

    if gh run list \
        --workflow "$CI_WORKFLOW" \
        --commit "$COMMIT" \
        --json databaseId,status,conclusion \
        --limit 20 \
        >"$CI_LOG" 2>"$LOG_DIR/ci_error.log"; then

        CI_RESULT="$(
            "$PYTHON" - "$CI_LOG" <<'PY'
import json
import sys

try:

    with open(
        sys.argv[1],
        encoding="utf-8",
    ) as handle:

        runs = json.load(handle)

except Exception:

    print("NOT VERIFIED")
    raise SystemExit(0)

completed = [
    run
    for run in runs
    if run.get("status") == "completed"
]

if not completed:

    print("NOT VERIFIED")

elif any(
    run.get("conclusion") == "success"
    for run in completed
):

    print("PASS")

elif any(
    run.get("conclusion") in {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
    }
    for run in completed
):

    print("FAIL")

else:

    print("NOT VERIFIED")

PY
        )"

        CI_STATUS="$CI_RESULT"

        CI_RUN_ID="$(
            "$PYTHON" - "$CI_LOG" <<'PY'
import json
import sys

try:

    with open(
        sys.argv[1],
        encoding="utf-8",
    ) as handle:

        runs = json.load(handle)

    completed = [
        run
        for run in runs
        if run.get("status") == "completed"
    ]

    print(
        completed[0].get("databaseId", "")
        if completed
        else ""
    )

except Exception:

    print("")

PY
        )"

    else

        CI_STATUS="NOT VERIFIED"

    fi

else

    CI_STATUS="NOT VERIFIED"

fi

echo
echo "GITHUB ACTIONS: $CI_STATUS"

echo "Workflow: $CI_WORKFLOW"

echo "Run ID: ${CI_RUN_ID:-NOT AVAILABLE}"


# =========================================================
# 8. CONSOLIDATED REPORT
# =========================================================

"$PYTHON" - \
    "$ROOT" \
    "$SOURCE_STATUS" \
    "$CONTRACT_STATUS" \
    "$FUNCTION_STATUS" \
    "$BEHAVIOR_STATUS" \
    "$COMPILE_STATUS" \
    "$PYTEST_STATUS" \
    "$PYTEST_COLLECTED" \
    "$PYTEST_PASSED" \
    "$PYTEST_FAILED" \
    "${PYTEST_ERRORS:-0}" \
    "${PYTEST_SKIPPED:-0}" \
    "$CI_STATUS" \
    "$CI_RUN_ID" \
    "$BRANCH" \
    "$COMMIT" \
    "$REPORT" <<'PY'

import json
import sys

from datetime import datetime, timezone
from pathlib import Path


(
    root,
    source_status,
    contract_status,
    function_status,
    behavior_status,
    compile_status,
    pytest_status,
    collected,
    passed,
    failed,
    errors,
    skipped,
    ci_status,
    ci_run_id,
    branch,
    commit,
    report_path,
) = sys.argv[1:]


root = Path(root)


def load_report(filename):

    path = root / "audit" / filename

    if not path.is_file():

        return {
            "status": "NOT VERIFIED",
            "reason": "Report file does not exist",
        }

    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:

        return {
            "status": "NOT VERIFIED",
            "error": str(exc),
        }


checks = {

    "source_integrity": source_status,

    "contract_integration": contract_status,

    "function_equivalence": function_status,

    "behavior_equivalence": behavior_status,

    "py_compile": compile_status,

    "pytest": pytest_status,

    "ci": ci_status,
}


statuses = list(
    checks.values()
)


if all(
    status == "PASS"
    for status in statuses
):

    final_result = "PASS"

elif "FAIL" in statuses:

    final_result = "FAIL"

else:

    final_result = "NOT VERIFIED"


report = {

    "audit_id": "P2-BENCH-CONFIG-01",

    "audit_version": "1.0",

    "timestamp_utc": datetime.now(
        timezone.utc
    ).isoformat(),

    "repository": (
        "adrianroman1/QFLPN-Quantum-Petri-Nets"
    ),

    "branch": branch,

    "commit": commit,

    "checks": checks,

    "source_integrity": load_report(
        "source_integrity.json"
    ),

    "contract_integration": load_report(
        "contract_integration.json"
    ),

    "function_equivalence": load_report(
        "function_equivalence.json"
    ),

    "behavior_equivalence": load_report(
        "behavior_equivalence.json"
    ),

    "pytest": {

        "status": pytest_status,

        "collected": int(collected),

        "passed": int(passed),

        "failed": int(failed),

        "errors": int(errors),

        "skipped": int(skipped),
    },

    "ci": {

        "status": ci_status,

        "workflow": "p2-validation.yml",

        "run_id": ci_run_id or None,

        "commit": commit,
    },

    "final_result": final_result,

    "acceptance": (
        "ACCEPTED"
        if final_result == "PASS"
        else "NOT ACCEPTED"
    ),
}


output = Path(report_path)

output.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)


print()

print("=" * 60)

print("P2-BENCH-CONFIG-01 AUDIT REPORT")

print("=" * 60)

for name, status in checks.items():

    print(
        f"{name:32} {status}"
    )

print("-" * 60)

print(
    f"{'FINAL RESULT':32} {final_result}"
)

print(
    f"{'ACCEPTANCE':32} {report['acceptance']}"
)

print("=" * 60)

print(
    f"Report: {output.relative_to(root)}"
)

PY


# =========================================================
# 9. FINAL EXIT CODE
# =========================================================

if \
    [ "$SOURCE_STATUS" = "PASS" ] && \
    [ "$CONTRACT_STATUS" = "PASS" ] && \
    [ "$FUNCTION_STATUS" = "PASS" ] && \
    [ "$BEHAVIOR_STATUS" = "PASS" ] && \
    [ "$COMPILE_STATUS" = "PASS" ] && \
    [ "$PYTEST_STATUS" = "PASS" ] && \
    [ "$CI_STATUS" = "PASS" ]; then

    echo
    echo "P2-BENCH-CONFIG-01: ACCEPTED"

    exit 0

else

    echo
    echo "P2-BENCH-CONFIG-01: NOT ACCEPTED"

    exit 1

fi
