from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "P1" / "artifacts"
TOL = 1e-12


def test_density_matrix_is_hermitian():
    rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
    residual = np.linalg.norm(rho - rho.conj().T, ord="fro")
    assert residual <= TOL
