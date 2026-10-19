"""Compute the formal numerical residuals for the canonical P1 instance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.tools.constants import NUMERICAL_TOLERANCE

ART = ROOT / "P1" / "artifacts"
OUT = ROOT / "P1" / "reports" / "residuals.json"


def finite(a: np.ndarray) -> bool:
    return bool(np.isfinite(a.real).all() and np.isfinite(a.imag).all())


def main() -> None:
    operator = np.load(ART / "operator.npy", allow_pickle=False)
    initial = np.load(ART / "initial_state.npy", allow_pickle=False)
    final = np.load(ART / "final_state.npy", allow_pickle=False)
    rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
    identity = np.eye(operator.shape[0], dtype=np.complex128)

    finite_checks = {
        "operator_finite": finite(operator),
        "initial_state_finite": finite(initial),
        "final_state_finite": finite(final),
        "density_matrix_finite": finite(rho),
    }
    trace_error = float(abs(np.trace(rho) - 1.0))
    hermiticity = float(np.linalg.norm(rho - rho.conj().T, ord="fro"))
    eigenvalues = np.linalg.eigvalsh((rho + rho.conj().T) / 2.0)
    psd = float(max(0.0, -float(np.min(eigenvalues))))
    unitarity = float(np.linalg.norm(operator.conj().T @ operator - identity, ord="fro"))
    state_norm_error = float(abs(np.linalg.norm(final) - 1.0))
    evolution_error = float(np.linalg.norm(final - operator @ initial, ord=2))
    pure_state_error = float(np.linalg.norm(rho - np.outer(final, final.conj()), ord="fro"))

    residuals = {
        "numerical_tolerance": NUMERICAL_TOLERANCE,
        "finite_checks": finite_checks,
        "operator_unitarity_frobenius": unitarity,
        "density_trace_absolute_error": trace_error,
        "density_hermiticity_frobenius": hermiticity,
        "density_psd_residual": psd,
        "state_norm_absolute_error": state_norm_error,
        "state_evolution_l2_residual": evolution_error,
        "pure_state_density_frobenius": pure_state_error,
        "minimum_density_eigenvalue": float(np.min(eigenvalues)),
    }
    residual_checks = {
        key: bool(value <= NUMERICAL_TOLERANCE)
        for key, value in {
            "operator_unitarity_frobenius": unitarity,
            "density_trace_absolute_error": trace_error,
            "density_hermiticity_frobenius": hermiticity,
            "density_psd_residual": psd,
            "state_norm_absolute_error": state_norm_error,
            "state_evolution_l2_residual": evolution_error,
            "pure_state_density_frobenius": pure_state_error,
        }.items()
    }
    passed = all(finite_checks.values()) and all(residual_checks.values())
    residuals["checks"] = {**finite_checks, **residual_checks}
    residuals["all_checks_pass"] = passed
    residuals["status"] = "PASS" if passed else "FAIL"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(residuals, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": residuals["status"], "checks": residuals["checks"]}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
