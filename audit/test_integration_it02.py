from copy import deepcopy

from audit.run_numeric_equivalence import (
    aggregate_operation_statuses,
    validate_numeric_report,
)


def test_it02_numeric_failure_propagation(valid_report):
    report = deepcopy(valid_report)

    operation = report["operations"]["rotation_operator"]

    operation["status"] = "FAIL"

    for comparison_name in (
        "baseline_vs_reference",
        "migrated_vs_reference",
        "baseline_vs_migrated",
    ):
        comparison = operation[comparison_name]
        comparison["status"] = "FAIL"
        comparison["frobenius_norm_error"] = 1e-3
        comparison["max_absolute_error"] = 1e-3

    report["components"]["operations_status"] = (
        aggregate_operation_statuses(report["operations"])
    )
    report["status"] = "FAIL"

    result = validate_numeric_report(report)

    assert report["components"]["operations_status"] == "FAIL"
    assert result["status"] == "PASS"
    assert report["status"] == "FAIL"
