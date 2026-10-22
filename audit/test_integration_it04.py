from copy import deepcopy

from audit.run_numeric_equivalence import (
    validate_numeric_report,
)


def test_it04_missing_function_equivalence_evidence(
    valid_report,
):
    report = deepcopy(valid_report)

    del report["migration_evidence"][
        "function_equivalence_status"
    ]

    report["migration_evidence"]["status"] = (
        "NOT VERIFIED"
    )
    report["components"]["migration_status"] = (
        "NOT VERIFIED"
    )
    report["status"] = "NOT VERIFIED"

    result = validate_numeric_report(report)

    assert result["status"] == "NOT VERIFIED"
    assert any(
        "migration" in error.lower()
        or "function_equivalence_status" in error
        for error in result["errors"]
    )
