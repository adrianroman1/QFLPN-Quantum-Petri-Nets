from copy import deepcopy

from audit.run_numeric_equivalence import (
    validate_numeric_report,
)


def test_it03_missing_pennylane_evidence(valid_report):
    report = deepcopy(valid_report)

    del report["pennylane_execution_checks"][
        "baseline_qnode_vs_reference"
    ]

    report["pennylane_execution_checks"]["status"] = (
        "NOT VERIFIED"
    )
    report["components"]["pennylane_status"] = (
        "NOT VERIFIED"
    )
    report["status"] = "NOT VERIFIED"

    result = validate_numeric_report(report)

    assert result["status"] == "NOT VERIFIED"
    assert any(
        "baseline_qnode_vs_reference" in error
        for error in result["errors"]
    )
