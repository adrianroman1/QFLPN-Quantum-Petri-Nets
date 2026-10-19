import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "P1" / "artifacts"
TOL = 1e-12


def test_density_matrix_trace_is_one():
    rho = np.load(ART / "density_matrix.npy", allow_pickle=False)
    assert abs(np.trace(rho) - 1.0) <= TOL
