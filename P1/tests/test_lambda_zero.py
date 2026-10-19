import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.code.qflpn_reference import fuzzy_to_angle
from P1.code.qflpn_transition_operator import ry

TOL = 1e-12


def test_zero_membership_maps_to_zero_angle_and_identity_rotation():
    theta = fuzzy_to_angle(0.0)
    assert abs(theta) <= TOL
    assert np_norm(ry(theta) - np_eye()) <= TOL


def np_norm(value):
    import numpy as np
    return float(np.linalg.norm(value, ord="fro"))


def np_eye():
    import numpy as np
    return np.eye(2, dtype=np.complex128)
