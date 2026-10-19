import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "P1" / "artifacts"
REPORT = ROOT / "P1" / "reports" / "independent_agreement.json"
TOL = 1e-12


def test_production_and_independent_operators_agree():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["operator_difference_frobenius"] <= TOL


def test_production_and_independent_state_vectors_agree():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["state_difference_l2"] <= TOL


def test_squared_pure_state_fidelity_is_one_within_tolerance():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["state_fidelity_error"] <= TOL
