from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "P1" / "artifacts"
TOL = 1e-12


def test_global_operator_is_unitary():
    operator = np.load(ART / "operator.npy", allow_pickle=False)
    identity = np.eye(operator.shape[0], dtype=np.complex128)
    residual = np.linalg.norm(operator.conj().T @ operator - identity, ord="fro")
    assert np.isfinite(residual)
    assert residual <= TOL
