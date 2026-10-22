from audit.run_numeric_equivalence import (
    validate_numeric_report,
)


def test_it01_valid_complete_report(valid_report):
    result = validate_numeric_report(valid_report)

    assert result["status"] == "PASS"
    assert result["errors"] == []

    assert valid_report["status"] == "PASS"
    assert valid_report["components"]["operations_status"] == "PASS"
    assert valid_report["components"]["artifacts_status"] == "PASS"
    assert valid_report["components"]["pennylane_status"] == "PASS"
    assert valid_report["components"]["migration_status"] == "PASS"

    assert "operations" in valid_report
    assert "artifacts" in valid_report
    assert "pennylane_execution_checks" in valid_report
    assert "migration_evidence" in valid_report
