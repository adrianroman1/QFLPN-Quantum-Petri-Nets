"""Publish the P1 validation evidence in the GitHub Actions job summary."""

from __future__ import annotations

import json
import math
import os
import platform
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "P1"
REPORTS = P1 / "reports"

SUMMARY_PATH = os.environ.get("GITHUB_STEP_SUMMARY")
VERDICT = os.environ.get("P1_VERDICT", "NOT_AVAILABLE")

NUMERICAL_REPORT = REPORTS / "residuals.json"
INDEPENDENT_REPORT = REPORTS / "independent_agreement.json"
TEST_REPORT = REPORTS / "test_log.json"
METADATA_REPORT = P1 / "artifacts" / "reference_instance.json"
ENVIRONMENT_REPORT = REPORTS / "environment.txt"


def read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON object without hiding malformed evidence."""

    if not path.is_file():
        return None

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return value if isinstance(value, dict) else None


def fmt(value: Any) -> str:
    """Format values safely for Markdown."""

    if value is None:
        return "N/A"

    if isinstance(value, bool):
        return "PASS" if value else "FAIL"

    if isinstance(value, float):
        if not math.isfinite(value):
            return "INVALID"
        return f"{value:.12g}"

    return str(value)


def markdown_escape(value: Any) -> str:
    """Prevent values from breaking Markdown table cells."""

    return fmt(value).replace("|", "\\|").replace("\n", " ")


def section(title: str) -> str:
    return f"\n## {title}\n"


def build_summary() -> str:
    lines: list[str] = []

    residuals = read_json(NUMERICAL_REPORT)
    independent = read_json(INDEPENDENT_REPORT)
    test_log = read_json(TEST_REPORT)
    metadata = read_json(METADATA_REPORT)

    lines.append("# QFLPN P1 — Validation Summary")
    lines.append("")

    lines.append(f"**Final verdict:** `{VERDICT}`")
    lines.append("")

    lines.append(
        "This summary displays generated validation evidence. "
        "The authoritative acceptance decision is made by "
        "`P1/tools/verify_final_package.py`."
    )

    # ---------------------------------------------------------
    # Test results
    # ---------------------------------------------------------

    lines.append(section("Automated tests"))

    if test_log is None:
        lines.append("`test_log.json` is missing or invalid.")
    else:
        pytest = test_log.get("pytest", {})

        if not isinstance(pytest, dict):
            pytest = {}

        lines.append("| Metric | Result |")
        lines.append("|---|---:|")
        lines.append(
            f"| Test log verdict | `{markdown_escape(test_log.get('verdict'))}` |"
        )
        lines.append(
            f"| Pytest exit code | {markdown_escape(pytest.get('exit_code'))} |"
        )
        lines.append(
            f"| Tests | {markdown_escape(pytest.get('tests'))} |"
        )
        lines.append(
            f"| Failures | {markdown_escape(pytest.get('failures'))} |"
        )
        lines.append(
            f"| Errors | {markdown_escape(pytest.get('errors'))} |"
        )
        lines.append(
            f"| Skipped | {markdown_escape(pytest.get('skipped'))} |"
        )

        checks = test_log.get("checks", {})

        if isinstance(checks, dict):
            lines.append("")
            lines.append("### Aggregated checks")
            lines.append("")
            lines.append("| Check | Result |")
            lines.append("|---|---:|")

            for key in sorted(checks):
                lines.append(
                    f"| `{markdown_escape(key)}` "
                    f"| {markdown_escape(checks[key])} |"
                )

        errors = test_log.get("errors", [])

        if isinstance(errors, list) and errors:
            lines.append("")
            lines.append("### Test aggregation errors")
            lines.append("")

            for error in errors:
                lines.append(f"- {markdown_escape(error)}")

    # ---------------------------------------------------------
    # Numerical residuals
    # ---------------------------------------------------------

    lines.append(section("Numerical residuals"))

    if residuals is None:
        lines.append("`residuals.json` is missing or invalid.")
    else:
        lines.append("| Residual | Value |")
        lines.append("|---|---:|")

        residual_keys = (
            "operator_unitarity_frobenius",
            "density_trace_absolute_error",
            "density_hermiticity_frobenius",
            "density_psd_residual",
            "state_norm_absolute_error",
            "state_evolution_l2_residual",
            "pure_state_density_frobenius",
        )

        for key in residual_keys:
            lines.append(
                f"| `{key}` | {markdown_escape(residuals.get(key))} |"
            )

        lines.append("")
        lines.append(
            f"- Numerical status: `{markdown_escape(residuals.get('status'))}`"
        )
        lines.append(
            "- All numerical checks: "
            f"`{markdown_escape(residuals.get('all_checks_pass'))}`"
        )
        lines.append(
            "- Tolerance: "
            f"`{markdown_escape(residuals.get('numerical_tolerance'))}`"
        )

    # ---------------------------------------------------------
    # Independent implementation
    # ---------------------------------------------------------

    lines.append(section("Independent implementation agreement"))

    if independent is None:
        lines.append(
            "`independent_agreement.json` is missing or invalid."
        )
    else:
        lines.append(
            f"- Status: `{markdown_escape(independent.get('status'))}`"
        )
        lines.append(
            "- All checks pass: "
            f"`{markdown_escape(independent.get('all_checks_pass'))}`"
        )
        lines.append(
            "- Numerical tolerance: "
            f"`{markdown_escape(independent.get('numerical_tolerance'))}`"
        )

        metrics = (
            "operator_difference_frobenius",
            "saved_operator_difference_frobenius",
            "constructive_operator_difference_frobenius",
            "state_difference_l2",
            "state_fidelity_error",
            "saved_final_state_difference_l2",
        )

        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---:|")

        for key in metrics:
            lines.append(
                f"| `{key}` | {markdown_escape(independent.get(key))} |"
            )

        checks = independent.get("checks", {})

        if isinstance(checks, dict):
            lines.append("")
            lines.append("### Independent checks")
            lines.append("")
            lines.append("| Check | Result |")
            lines.append("|---|---:|")

            for key in sorted(checks):
                lines.append(
                    f"| `{markdown_escape(key)}` "
                    f"| {markdown_escape(checks[key])} |"
                )

    # ---------------------------------------------------------
    # Canonical instance metadata
    # ---------------------------------------------------------

    lines.append(section("Canonical reference instance"))

    if metadata is None:
        lines.append(
            "`reference_instance.json` is missing or invalid."
        )
    else:
        fields = (
            ("Instance ID", "instance_id"),
            ("Qubit count", "qubit_count"),
            ("Hilbert dimension", "hilbert_space_dimension"),
            ("Basis ordering", "basis_ordering"),
            ("Numeric dtype", "numeric_dtype"),
            ("Python version", "python_version"),
            ("NumPy version", "numpy_version"),
            ("SciPy version", "scipy_version"),
            ("Repository revision", "repository_revision"),
        )

        lines.append("| Field | Value |")
        lines.append("|---|---|")

        for label, key in fields:
            lines.append(
                f"| {label} | `{markdown_escape(metadata.get(key))}` |"
            )

    # ---------------------------------------------------------
    # Execution environment
    # ---------------------------------------------------------

    lines.append(section("Execution environment"))

    if ENVIRONMENT_REPORT.is_file():
        lines.append(
            "Full runner information is available in "
            "`P1/reports/environment.txt` and in the downloadable "
            "workflow artifact."
        )
        lines.append("")
        lines.append("```text")

        try:
            environment = ENVIRONMENT_REPORT.read_text(
                encoding="utf-8"
            ).strip()

            # Keep the Actions Summary readable.
            environment_lines = environment.splitlines()
            lines.extend(environment_lines[:45])

            if len(environment_lines) > 45:
                lines.append("... full environment report in artifact ...")

        except OSError as exc:
            lines.append(f"Unable to read environment report: {exc}")

        lines.append("```")
    else:
        lines.append("`environment.txt` is missing.")

    # ---------------------------------------------------------
    # Timing clarification
    # ---------------------------------------------------------

    lines.append(section("Execution time"))

    lines.append(
        "GitHub Actions records the duration of every workflow step "
        "and the total job duration in the workflow run interface."
    )
    lines.append("")
    lines.append(
        "P1 does not currently define a dedicated sequential-versus-parallel "
        "performance benchmark. Therefore, no algorithmic speedup is "
        "reported here."
    )

    # ---------------------------------------------------------
    # Artifact paths
    # ---------------------------------------------------------

    lines.append(section("Evidence files"))

    artifact_paths = (
        "P1/artifacts/reference_instance.json",
        "P1/artifacts/operator.npy",
        "P1/artifacts/initial_state.npy",
        "P1/artifacts/final_state.npy",
        "P1/artifacts/density_matrix.npy",
        "P1/reports/environment.txt",
        "P1/reports/residuals.json",
        "P1/reports/independent_agreement.json",
        "P1/reports/test_log.json",
        "P1/MANIFEST.txt",
        "P1/SHA256SUMS.txt",
    )

    for path in artifact_paths:
        full_path = ROOT / path
        status = "present" if full_path.is_file() else "missing"
        lines.append(f"- `{path}` — {status}")

    lines.append("")
    lines.append("---")
    lines.append(
        "Generated automatically by "
        "`P1/tools/write_github_summary.py`."
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    summary = build_summary()

    if SUMMARY_PATH:
        with open(
            SUMMARY_PATH,
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(summary)

        print("P1 GitHub Actions Summary published.")
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
