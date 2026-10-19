import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.code.qflpn_reference import fuzzy_to_angle
from P1.code.qflpn_transition_operator import ry

TOL = 1e-12


def test_unit_membership_maps_to_pi_angle():
    theta = fuzzy_to_angle(1.0)
    assert abs(theta - math.pi) <= TOL
    import numpy as np
    expected = np.array([[0.0, -1.0], [1.0, 0.0]], dtype=np.complex128)
    assert np.linalg.norm(ry(theta) - expected, ord="fro") <= TOL
