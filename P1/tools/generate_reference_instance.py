"""Generate the canonical four-qubit P1 numerical instance."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from P1.code.qflpn_reference import fuzzy_to_angle
from P1.code.qflpn_transition_operator import qflpn_transition_operator
from P1.tools.constants import (
    BASIS_ORDERING, CANONICAL_MEMBERSHIPS, GATE_SEQUENCE,
    HILBERT_SPACE_DIMENSION, INITIAL_STATE_LABEL, NUMERIC_DTYPE,
    OPERATOR_EXPRESSION, QUBIT_COUNT,
)

P1 = ROOT / "P1"
ARTIFACTS = P1 / "artifacts"


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    memberships = [float(x) for x in CANONICAL_MEMBERSHIPS]
    angles = [float(fuzzy_to_angle(x)) for x in memberships]
    operator = np.asarray(qflpn_transition_operator(memberships), dtype=np.complex128)
    initial_state = np.zeros(HILBERT_SPACE_DIMENSION, dtype=np.complex128)
    initial_state[0] = 1.0 + 0.0j
    final_state = operator @ initial_state
    density_matrix = np.outer(final_state, final_state.conj()).astype(np.complex128)

    arrays = {
        "operator.npy": operator,
        "initial_state.npy": initial_state,
        "final_state.npy": final_state,
        "density_matrix.npy": density_matrix,
    }
    for filename, array in arrays.items():
        if not np.isfinite(array.real).all() or not np.isfinite(array.imag).all():
            raise ValueError(f"Non-finite values in {filename}")
        np.save(ARTIFACTS / filename, array, allow_pickle=False)

    try:
        scipy_version = version("scipy")
    except Exception as exc:  # fail visibly; the locked environment requires SciPy
        raise RuntimeError("SciPy version could not be determined") from exc

    metadata = {
        "schema_version": 1,
        "instance_id": "P1-CANONICAL-4Q-001",
        "qubit_count": QUBIT_COUNT,
        "hilbert_space_dimension": HILBERT_SPACE_DIMENSION,
        "basis_ordering": BASIS_ORDERING,
        "qubit_indexing": "qubit 0 is the leftmost tensor factor; qubit 3 is the rightmost",
        "initial_state_label": INITIAL_STATE_LABEL,
        "initial_state_basis_index": 0,
        "memberships": memberships,
        "theta_formula": "theta_i = 2 * asin(sqrt(lambda_i))",
        "angles_rad": angles,
        "operator_expression": OPERATOR_EXPRESSION,
        "gate_sequence": GATE_SEQUENCE,
        "c3x_controls": [0, 1, 2],
        "c3x_target": 3,
        "composition_convention": "rightmost operator acts first",
        "numeric_dtype": NUMERIC_DTYPE,
        "array_serialization": "NumPy .npy, allow_pickle=False, C-order arrays",
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "scipy_version": scipy_version,
        "platform": platform.platform(),
        "repository_revision": git_revision(),
    }
    (ARTIFACTS / "reference_instance.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Generated canonical instance in {ARTIFACTS}")


if __name__ == "__main__":
    main()
