#!/usr/bin/env python3
"""
P2-BENCH-CONFIG-01
Function Body and AST Equivalence Audit.

Baseline validator:
eb6f382fb70a1f04750b72931ef54f77eb28c470

Baseline runner:
03a63fec41a099944017d9c95d53c3b8656359a3

Compara exclusiv funcțiile top-level.
Ignoră comentariile și whitespace-ul prin normalizare AST.
Nu modifică sursele.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess

from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit"

VALIDATOR_PATH = (
    ROOT / "P2" / "benchmarks" / "validate_benchmark.py"
)

RUNNER_PATH = (
    ROOT / "P2" / "benchmarks" / "benchmark_runner.py"
)

VALIDATOR_BASELINE_BLOB = (
    "eb6f382fb70a1f04750b72931ef54f77eb28c470"
)

RUNNER_BASELINE_BLOB = (
    "03a63fec41a099944017d9c95d53c3b8656359a3"
)

PROTECTED_VALIDATOR_FUNCTIONS = {
    "finite_number",
    "close",
    "require_number",
    "validate_statistics",
    "validate_world_record",
    "validate_paired_samples",
    "validate_operation",
    "validate_report",
    "validate_csv",
    "markdown_number_matches",
    "validate_environment",
    "remove_benchmark_cache",
}

AUTHORIZED_VALIDATOR_CHANGES = {
    "validate_markdown",
    "validate_results",
    "main",
}

CRITICAL_RUNNER_FUNCTIONS = {
    "statistics_for",
    "numerical_error",
    "build_operations",
    "time_paired_operation",
}


def git_blob(blob_sha: str) -> bytes:
    """Recuperează un blob exclusiv din obiectele Git."""

    object_type = subprocess.run(
        ["git", "cat-file", "-t", blob_sha],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    if object_type != "blob":
        raise ValueError(
            f"Git object {blob_sha} is {object_type}, not blob"
        )

    return subprocess.run(
        ["git", "cat-file", "blob", blob_sha],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def parse_source(
    source: bytes,
    filename: str,
) -> ast.Module:

    return ast.parse(
        source.decode("utf-8"),
        filename=filename,
    )


def collect_top_level_functions(
    tree: ast.Module,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """
    Colectează numai funcțiile top-level.

    Funcțiile nested și metodele claselor nu sunt amestecate
    cu API-ul public al modulului.
    """

    return {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


def normalized_ast(node: ast.AST) -> str:
    """Normalizare AST fără poziții de sursă."""

    return ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )


def function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    """
    Include:
    - argumente și ordine;
    - valori implicite;
    - keyword-only;
    - annotations;
    - return annotation;
    - tipul funcției sync/async;
    - decoratorii.
    """

    payload = {
        "kind": type(node).__name__,
        "arguments": normalized_ast(node.args),
        "returns": (
            normalized_ast(node.returns)
            if node.returns is not None
            else None
        ),
        "decorators": [
            normalized_ast(decorator)
            for decorator in node.decorator_list
        ],
    }

    return json.dumps(
        payload,
        sort_keys=True,
    )


def function_body(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:

    return "\n".join(
        normalized_ast(statement)
        for statement in node.body
    )


def compare_function_sets(
    original: dict,
    current: dict,
    expected: set[str],
    *,
    protected: set[str] | None = None,
) -> dict:

    protected = protected or set()

    missing = sorted(
        expected - set(current)
    )

    added = sorted(
        set(current) - expected
    )

    signature_changed = []
    body_changed = []
    identical = []

    for name in sorted(expected):

        if name not in original or name not in current:
            continue

        old = original[name]
        new = current[name]

        if function_signature(old) != function_signature(new):

            signature_changed.append(name)

        elif function_body(old) != function_body(new):

            body_changed.append(name)

        else:

            identical.append(name)

    protected_failures = sorted(
        set(signature_changed + body_changed)
        & protected
    )

    status = (
        "FAIL"
        if (
            missing
            or added
            or protected_failures
        )
        else "PASS"
    )

    return {
        "status": status,
        "expected_count": len(expected),
        "present_count": len(expected) - len(missing),
        "missing": missing,
        "unexpected_top_level_functions": added,
        "signature_changed": signature_changed,
        "body_changed": body_changed,
        "identical": identical,
        "protected_changes": protected_failures,
    }


def audit_validator() -> dict:

    original_bytes = git_blob(
        VALIDATOR_BASELINE_BLOB
    )

    current_bytes = VALIDATOR_PATH.read_bytes()

    original_tree = parse_source(
        original_bytes,
        "validator-original",
    )

    current_tree = parse_source(
        current_bytes,
        str(VALIDATOR_PATH),
    )

    original_functions = collect_top_level_functions(
        original_tree
    )

    current_functions = collect_top_level_functions(
        current_tree
    )

    expected = (
        PROTECTED_VALIDATOR_FUNCTIONS
        | AUTHORIZED_VALIDATOR_CHANGES
    )

    comparison = compare_function_sets(
        original_functions,
        current_functions,
        expected,
        protected=PROTECTED_VALIDATOR_FUNCTIONS,
    )

    comparison.update({
        "baseline_blob": VALIDATOR_BASELINE_BLOB,
        "baseline_sha256": hashlib.sha256(
            original_bytes
        ).hexdigest(),
        "current_sha256": hashlib.sha256(
            current_bytes
        ).hexdigest(),
        "protected_functions": sorted(
            PROTECTED_VALIDATOR_FUNCTIONS
        ),
        "authorized_changes": sorted(
            AUTHORIZED_VALIDATOR_CHANGES
        ),
    })

    return comparison


def audit_runner() -> dict:

    original_bytes = git_blob(
        RUNNER_BASELINE_BLOB
    )

    current_bytes = RUNNER_PATH.read_bytes()

    original_tree = parse_source(
        original_bytes,
        "runner-original",
    )

    current_tree = parse_source(
        current_bytes,
        str(RUNNER_PATH),
    )

    original_functions = collect_top_level_functions(
        original_tree
    )

    current_functions = collect_top_level_functions(
        current_tree
    )

    # Nu presupunem că funcțiile care nu există în baseline
    # pot fi validate prin comparație.
    available = (
        CRITICAL_RUNNER_FUNCTIONS
        & set(original_functions)
    )

    unavailable = sorted(
        CRITICAL_RUNNER_FUNCTIONS - available
    )

    if not available:

        return {
            "status": "NOT VERIFIED",
            "reason": (
                "None of the configured critical function names "
                "were found in the runner baseline. The audit "
                "cannot establish their source module."
            ),
            "requested_functions": sorted(
                CRITICAL_RUNNER_FUNCTIONS
            ),
            "unavailable_in_baseline": unavailable,
        }

    comparison = compare_function_sets(
        original_functions,
        current_functions,
        available,
        protected=available,
    )

    if unavailable and comparison["status"] == "PASS":

        comparison["status"] = "NOT VERIFIED"

    comparison.update({
        "baseline_blob": RUNNER_BASELINE_BLOB,
        "baseline_sha256": hashlib.sha256(
            original_bytes
        ).hexdigest(),
        "current_sha256": hashlib.sha256(
            current_bytes
        ).hexdigest(),
        "requested_functions": sorted(
            CRITICAL_RUNNER_FUNCTIONS
        ),
        "compared_functions": sorted(available),
        "unavailable_in_baseline": unavailable,
    })

    return comparison


def main() -> int:

    report = {
        "audit": "function_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "validator": {},
        "runner": {},
        "status": "NOT VERIFIED",
        "issues": [],
    }

    try:

        report["validator"] = audit_validator()

    except Exception as exc:

        report["validator"] = {
            "status": "NOT VERIFIED",
            "error": str(exc),
        }

        report["issues"].append(
            f"Validator comparison unavailable: {exc}"
        )

    try:

        report["runner"] = audit_runner()

    except Exception as exc:

        report["runner"] = {
            "status": "NOT VERIFIED",
            "error": str(exc),
        }

        report["issues"].append(
            f"Runner comparison unavailable: {exc}"
        )

    states = [
        report["validator"]["status"],
        report["runner"]["status"],
    ]

    if "FAIL" in states:

        report["status"] = "FAIL"

    elif all(state == "PASS" for state in states):

        report["status"] = "PASS"

    else:

        report["status"] = "NOT VERIFIED"

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = AUDIT_DIR / "function_equivalence.json"

    output.write_text(
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

    return (
        1
        if report["status"] == "FAIL"
        else 0
    )


if __name__ == "__main__":

    raise SystemExit(main())
