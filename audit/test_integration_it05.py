from copy import deepcopy

from audit.run_numeric_equivalence import (
    validate_numeric_report,
)


def test_it05_declared_global_status_mismatch(
    valid_report,
):
    report = deepcopy(valid_report)

    report["migration_evidence"]["status"] = (
        "NOT VERIFIED"
    )
    report["components"]["migration_status"] = (
        "NOT VERIFIED"
    )

    # Contradicție intenționată:
    report["status"] = "PASS"

    result = validate_numeric_report(report)

    assert result["status"] == "FAIL"
    assert any(
        "status" in error.lower()
        and (
            "contradict" in error.lower()
            or "mismatch" in error.lower()
        )
        for error in result["errors"]
    )
