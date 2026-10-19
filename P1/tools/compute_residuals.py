"""Compute formal numerical residuals for the canonical P1 instance."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from P1.tools.constants import (
    HILBERT_SPACE_DIMENSION,
    NUMERICAL_TOLERANCE,
)

ART = ROOT / "P1" / "artifacts"
OUT = ROOT / "P1" / "reports" / "residuals.json"

EXPECTED_SHAPES = {
    "operator": (
        HILBERT_SPACE_DIMENSION,
        HILBERT_SPACE_DIMENSION,
    ),
    "initial_state": (HILBERT_SPACE_DIMENSION,),
    "final_state": (HILBERT_SPACE_DIMENSION,),
    "density_matrix": (
        HILBERT_SPACE_DIMENSION,
        HILBERT_SPACE_DIMENSION,
    ),
}

FINITE_CHECK_KEYS = (
    "operator_finite",
    "initial_state_finite",
    "final_state_finite",
    "density_matrix_finite",
)

RESIDUAL_KEYS = (
    "operator_unitarity_frobenius",
    "density_trace_absolute_error",
    "density_hermiticity_frobenius",
    "density_psd_residual",
    "state_norm_absolute_error",
    "state_evolution_l2_residual",
    "pure_state_density_frobenius",
)


def finite(array: np.ndarray) -> bool:
    """Return True only when every real and imaginary component is finite."""
    try:
        return bool(
            np.isfinite(array.real).all()
            and np.isfinite(array.imag).all()
        )
    except (TypeError, ValueError, AttributeError):
        return False


def write_report(report: dict[str, Any]) -> None:
    """Write a deterministic JSON report."""
    OUT.parent.mkdir(parents=True, exist_ok=True)

    OUT.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def failure_report(
    reason: str,
    finite_checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a machine-readable FAIL report without fabricated metrics."""
    if finite_checks is None:
        finite_checks = {
            key: False
            for key in FINITE_CHECK_KEYS
        }

    residual_checks = {
        key: False
        for key in RESIDUAL_KEYS
    }

    checks = {
        **finite_checks,
        **residual_checks,
    }

    report = {
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "finite_checks": finite_checks,
        "operator_unitarity_frobenius": None,
        "density_trace_absolute_error": None,
        "density_hermiticity_frobenius": None,
        "density_psd_residual": None,
        "state_norm_absolute_error": None,
        "state_evolution_l2_residual": None,
        "pure_state_density_frobenius": None,
        "minimum_density_eigenvalue": None,
        "checks": checks,
        "all_checks_pass": False,
        "status": "FAIL",
        "error": reason,
    }

    return report


def load_artifacts() -> dict[str, np.ndarray]:
    """Load all canonical arrays without permitting pickle execution."""
    filenames = {
        "operator": ART / "operator.npy",
        "initial_state": ART / "initial_state.npy",
        "final_state": ART / "final_state.npy",
        "density_matrix": ART / "density_matrix.npy",
    }

    arrays: dict[str, np.ndarray] = {}

    for name, path in filenames.items():
        if not path.is_file():
            raise FileNotFoundError(
                f"Required artifact does not exist: {path}"
            )

        arrays[name] = np.load(
            path,
            allow_pickle=False,
        )

    return arrays


def validate_shapes(
    arrays: dict[str, np.ndarray],
) -> None:
    """Reject arrays whose shapes differ from the canonical instance."""
    for name, expected_shape in EXPECTED_SHAPES.items():
        actual_shape = arrays[name].shape

        if actual_shape != expected_shape:
            raise ValueError(
                f"{name} shape mismatch: "
                f"expected {expected_shape}, got {actual_shape}"
            )


def validate_numeric_dtypes(
    arrays: dict[str, np.ndarray],
) -> None:
    """Reject non-numeric and object arrays before numerical operations."""
    for name, array in arrays.items():
        if array.dtype.kind not in ("i", "u", "f", "c"):
            raise TypeError(
                f"{name} has unsupported dtype: {array.dtype}"
            )


def calculate_residuals(
    arrays: dict[str, np.ndarray],
    finite_checks: dict[str, bool],
) -> dict[str, Any]:
    """Calculate the canonical P1 residuals after input validation."""
    operator = np.asarray(
        arrays["operator"],
        dtype=np.complex128,
    )
    initial = np.asarray(
        arrays["initial_state"],
        dtype=np.complex128,
    )
    final = np.asarray(
        arrays["final_state"],
        dtype=np.complex128,
    )
    rho = np.asarray(
        arrays["density_matrix"],
        dtype=np.complex128,
    )

    identity = np.eye(
        HILBERT_SPACE_DIMENSION,
        dtype=np.complex128,
    )

    trace_error = float(
        abs(np.trace(rho) - 1.0)
    )

    hermiticity = float(
        np.linalg.norm(
            rho - rho.conj().T,
            ord="fro",
        )
    )

    hermitian_rho = (
        rho + rho.conj().T
    ) / 2.0

    eigenvalues = np.linalg.eigvalsh(
        hermitian_rho
    )

    minimum_eigenvalue = float(
        np.min(eigenvalues)
    )

    psd = float(
        max(0.0, -minimum_eigenvalue)
    )

    unitarity = float(
        np.linalg.norm(
            operator.conj().T @ operator - identity,
            ord="fro",
        )
    )

    state_norm_error = float(
        abs(np.linalg.norm(final) - 1.0)
    )

    evolution_error = float(
        np.linalg.norm(
            final - operator @ initial,
            ord=2,
        )
    )

    pure_state_error = float(
        np.linalg.norm(
            rho - np.outer(final, final.conj()),
            ord="fro",
        )
    )

    metrics = {
        "operator_unitarity_frobenius": unitarity,
        "density_trace_absolute_error": trace_error,
        "density_hermiticity_frobenius": hermiticity,
        "density_psd_residual": psd,
        "state_norm_absolute_error": state_norm_error,
        "state_evolution_l2_residual": evolution_error,
        "pure_state_density_frobenius": pure_state_error,
    }

    if not all(
        np.isfinite(value)
        for value in metrics.values()
    ):
        raise ArithmeticError(
            "One or more calculated residuals are non-finite"
        )

    residual_checks = {
        key: bool(
            value <= NUMERICAL_TOLERANCE
        )
        for key, value in metrics.items()
    }

    checks = {
        **finite_checks,
        **residual_checks,
    }

    passed = (
        all(finite_checks.values())
        and all(residual_checks.values())
    )

    return {
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "finite_checks": finite_checks,
        **metrics,
        "minimum_density_eigenvalue": minimum_eigenvalue,
        "checks": checks,
        "all_checks_pass": passed,
        "status": "PASS" if passed else "FAIL",
    }


def main() -> None:
    """Validate inputs, calculate residuals, and always emit a report."""
    try:
        arrays = load_artifacts()

        validate_shapes(arrays)
        validate_numeric_dtypes(arrays)

        finite_checks = {
            "operator_finite": finite(arrays["operator"]),
            "initial_state_finite": finite(arrays["initial_state"]),
            "final_state_finite": finite(arrays["final_state"]),
            "density_matrix_finite": finite(
                arrays["density_matrix"]
            ),
        }

        if not all(finite_checks.values()):
            invalid = [
                key
                for key, value in finite_checks.items()
                if not value
            ]

            report = failure_report(
                "Non-finite values detected: "
                + ", ".join(invalid),
                finite_checks,
            )

            write_report(report)

            print(
                json.dumps(
                    {
                        "status": "FAIL",
                        "error": report["error"],
                        "checks": report["checks"],
                    },
                    indent=2,
                )
            )

            raise SystemExit(1)

        report = calculate_residuals(
            arrays,
            finite_checks,
        )

        write_report(report)

        print(
            json.dumps(
                {
                    "status": report["status"],
                    "checks": report["checks"],
                },
                indent=2,
            )
        )

        if report["status"] != "PASS":
            raise SystemExit(1)

    except SystemExit:
        raise

    except Exception as exc:
        report = failure_report(
            f"{type(exc).__name__}: {exc}"
        )

        try:
            write_report(report)
        except Exception as write_exc:
            print(
                "FATAL: could not write residual report: "
                f"{type(write_exc).__name__}: {write_exc}",
                file=sys.stderr,
            )
            raise SystemExit(2) from write_exc

        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": report["error"],
                    "checks": report["checks"],
                },
                indent=2,
            )
        )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
