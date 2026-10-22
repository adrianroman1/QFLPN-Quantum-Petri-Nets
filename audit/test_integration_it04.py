from copy import deepcopy

from audit.run_numeric_equivalence import (
    validate_numeric_report,
)


def test_it04_missing_function_equivalence_evidence(
    valid_report,
):
    report = deepcopy(valid_report)

    report["migration_evidence"][
        "function_equivalence_status"
    ] = "NOT VERIFIED"

    report["migration_evidence"][
        "numeric_equivalence_status"
    ] = "PASS"

    report["migration_evidence"]["status"] = "NOT VERIFIED"

    report["components"]["migration_status"] = "NOT VERIFIED"
    report["status"] = "NOT VERIFIED"

    result = validate_numeric_report(report)

    assert result["status"] == "PASS"
    assert report["status"] == "NOT VERIFIED"
