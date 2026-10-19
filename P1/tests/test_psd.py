from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "P1" / "artifacts"
TOL = 1e-12


def test_density_matrix_is_positive_semidefinite():
    rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
    eigenvalues = np.linalg.eigvalsh((rho + rho.conj().T) / 2.0)
    residual = max(0.0, -float(eigenvalues.min()))
    assert residual <= TOL
