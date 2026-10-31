#!/usr/bin/env python3
"""Tests for P3/hpc/tools/generate_hpc_benchmark_proposal.py.

The tests verify proposal generation from hpc-target.json.
They do not run SpMV and do not create measured benchmark results.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL = (
    ROOT
    / "P3"
    / "hpc"
    / "tools"
    / "generate_hpc_benchmark_proposal.py"
)
CONFIG = ROOT / "P3" / "hpc" / "config" / "hpc-target.json"

SPEC = importlib.util.spec_from_file_location(
    "qflpn_generate_hpc_benchmark_proposal",
    TOOL,
)
assert SPEC is not None and SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def valid_config() -> dict[str, Any]:
    return load_config()


def validated_parts(
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return MODULE.validate_config(config)


def build_report(
    config: dict[str, Any],
    source_path: Path | None = None,
) -> dict[str, Any]:
    hardware, benchmark = validated_parts(config)
    return MODULE.build_proposal(
        config,
        hardware,
        benchmark,
        source_path or CONFIG,
    )


def test_repository_configuration_exists_and_uses_target_v2() -> None:
    assert CONFIG.is_file()

    config = load_config()

    assert config["schema"] == "qflpn-p3-hpc-target-v2"
    assert config["status"] == (
        "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE"
    )


def test_generator_accepts_repository_configuration() -> None:
    config = load_config()

    hardware, benchmark = MODULE.validate_config(config)

    assert hardware["compute_nodes"] == 16
    assert hardware["physical_cores_total"] == 664
    assert hardware["ram_gib_total"] == 4096
    assert hardware["ram_gib_per_node"] == 256

    assert benchmark["workload"] == "SpMV"
    assert benchmark["parallelism_target"] == 664
    assert benchmark["maximum_target_dimension"] == 10_000_000
    assert benchmark["execution_status"] == "NOT_EXECUTED"


def test_proposal_preserves_exact_664_worker_target() -> None:
    config = load_config()
    report = build_report(config)

    benchmark = report["benchmark"]

    assert benchmark["parallelism_target"] == 664
    assert benchmark["worker_counts"] == [
        1, 2, 4, 8, 16, 32,
        64, 128, 256, 512, 640, 664,
    ]
    assert 672 not in benchmark["worker_counts"]


def test_proposal_preserves_10m_dimension_threshold() -> None:
    config = load_config()
    report = build_report(config)

    benchmark = report["benchmark"]

    assert benchmark["maximum_target_dimension"] == 10_000_000
    assert benchmark["thresholds"][-1] == 10_000_000
    assert 10_000_000 in benchmark["thresholds"]


def test_proposal_preserves_warmup_and_measurement_requirements() -> None:
    report = build_report(load_config())
    benchmark = report["benchmark"]

    assert benchmark["minimum_warmup"] == 5
    assert benchmark["minimum_valid_measurements"] == 30


def test_proposal_includes_hardware_topology() -> None:
    report = build_report(load_config())
    hardware = report["hardware_target"]

    assert hardware["compute_nodes"] == 16
    assert hardware["physical_cores_total"] == 664

    assert hardware["node_groups"] == [
        {
            "names": "HPC-01..HPC-08",
            "nodes": 8,
            "physical_cores_per_node": 42,
            "group_physical_cores": 336,
        },
        {
            "names": "HPC-09..HPC-16",
            "nodes": 8,
            "physical_cores_per_node": 41,
            "group_physical_cores": 328,
        },
    ]

    assert sum(
        group["group_physical_cores"]
        for group in hardware["node_groups"]
    ) == 664


def test_proposal_includes_motherboard_collection_requirements() -> None:
    report = build_report(load_config())
    board = report["hardware_target"]["motherboard"]

    assert board["collection_required"] is True
    assert board["collection_scope"] == "EACH_COMPUTE_NODE"
    assert board["fields"] == [
        "manufacturer",
        "model",
        "version",
    ]
    assert board["source"] == "/sys/class/dmi/id/"
    assert board["missing_value"] == "UNAVAILABLE"


def test_proposal_does_not_invent_motherboard_values() -> None:
    config = load_config()
    report = build_report(config)

    board = report["hardware_target"]["motherboard"]

    assert "manufacturer" not in board
    assert "model" not in board
    assert "version" not in board

    assert board["collection_required"] is True
    assert board["collection_scope"] == "EACH_COMPUTE_NODE"


def test_proposal_is_explicitly_not_execution_evidence() -> None:
    report = build_report(load_config())

    assert report["status"] == "PROPOSED_NOT_EXECUTED"
    assert report["evidence_classification"] == (
        "CONFIGURATION_ONLY_NOT_PERFORMANCE_EVIDENCE"
    )

    evidence = report["execution_evidence"]

    assert evidence["benchmark_executed"] is False
    assert evidence["664_worker_execution_demonstrated"] is False
    assert evidence["dimension_10000000_execution_demonstrated"] is False
    assert evidence["measured_performance_claims"] is False


def test_proposal_declares_p3_validation_integrity_scope() -> None:
    report = build_report(load_config())
    integrity = report["integrity_scope"]

    assert integrity["workflow_job"] == "p3_validation"
    assert integrity["must_be_included_in_manifest"] == "P3/MANIFEST.txt"
    assert integrity["must_be_included_in_checksums"] == "P3/SHA256SUMS.txt"


def test_generator_rejects_wrong_configuration_schema() -> None:
    config = valid_config()
    config["schema"] = "qflpn-p3-hpc-configuration"

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_non_proposed_configuration_status() -> None:
    config = valid_config()
    config["status"] = "ACCEPTED"

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_missing_hardware_target() -> None:
    config = valid_config()
    del config["hardware_target"]

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_missing_benchmark_section() -> None:
    config = valid_config()
    del config["benchmark"]

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_inconsistent_node_count() -> None:
    config = valid_config()
    config["hardware_target"]["compute_nodes"] = 15

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_inconsistent_physical_core_total() -> None:
    config = valid_config()
    config["hardware_target"]["physical_cores_total"] = 672

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_inconsistent_ram_total() -> None:
    config = valid_config()
    config["hardware_target"]["ram_gib_total"] = 4095

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_missing_motherboard_collection() -> None:
    config = valid_config()
    config["hardware_target"]["motherboard"]["collection_required"] = False

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_incomplete_motherboard_fields() -> None:
    config = valid_config()
    config["hardware_target"]["motherboard"]["fields"] = [
        "manufacturer",
        "model",
    ]

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_wrong_motherboard_missing_value() -> None:
    config = valid_config()
    config["hardware_target"]["motherboard"]["missing_value"] = "UNKNOWN"

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_wrong_workload() -> None:
    config = valid_config()
    config["benchmark"]["workload"] = "DenseMatrixMultiplication"

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_parallelism_other_than_664() -> None:
    config = valid_config()
    config["benchmark"]["parallelism_target"] = 672

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_worker_counts_without_664() -> None:
    config = valid_config()
    config["benchmark"]["worker_counts"].remove(664)

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_unsorted_worker_counts() -> None:
    config = valid_config()
    config["benchmark"]["worker_counts"] = [1, 4, 2, 664]

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_duplicate_worker_counts() -> None:
    config = valid_config()
    config["benchmark"]["worker_counts"] = [1, 2, 2, 664]

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_maximum_dimension_other_than_10m() -> None:
    config = valid_config()
    config["benchmark"]["maximum_target_dimension"] = 1_000_000

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_thresholds_without_10m() -> None:
    config = valid_config()
    config["benchmark"]["thresholds"].remove(10_000_000)

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_unsorted_thresholds() -> None:
    config = valid_config()
    config["benchmark"]["thresholds"] = [256, 1024, 512, 10_000_000]

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_warmup_below_five() -> None:
    config = valid_config()
    config["benchmark"]["minimum_warmup"] = 4

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_measurements_below_thirty() -> None:
    config = valid_config()
    config["benchmark"]["minimum_valid_measurements"] = 29

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_generator_rejects_execution_status_other_than_not_executed() -> None:
    config = valid_config()
    config["benchmark"]["execution_status"] = "EXECUTED"

    with pytest.raises(MODULE.ProposalError):
        MODULE.validate_config(config)


def test_markdown_contains_hardware_and_benchmark_proposal() -> None:
    report = build_report(load_config())
    markdown = MODULE.build_markdown(report)

    assert "# QFLPN P3 — HPC Benchmark Proposal" in markdown
    assert "## 1. Hardware target" in markdown
    assert "### Compute-node topology" in markdown
    assert "### Motherboard inventory requirements" in markdown
    assert "## 2. SpMV benchmark proposal" in markdown

    assert "664" in markdown
    assert "10,000,000" in markdown
    assert "HPC-01..HPC-08" in markdown
    assert "HPC-09..HPC-16" in markdown
    assert "manufacturer, model, version" in markdown


def test_markdown_marks_proposal_as_not_executed() -> None:
    report = build_report(load_config())
    markdown = MODULE.build_markdown(report)

    assert "PROPOSED — NOT EXECUTED" in markdown
    assert "`NOT_EXECUTED`" in markdown
    assert "664-worker execution demonstrated: `false`" in markdown
    assert "Dimension 10,000,000 execution demonstrated: `false`" in markdown
    assert "Measured performance claims: `false`" in markdown


def test_markdown_references_p3_validation_manifest_and_checksums() -> None:
    report = build_report(load_config())
    markdown = MODULE.build_markdown(report)

    assert "`p3_validation`" in markdown
    assert "`P3/MANIFEST.txt`" in markdown
    assert "`P3/SHA256SUMS.txt`" in markdown


def test_json_and_markdown_outputs_are_generated_from_same_proposal(
    tmp_path: Path,
) -> None:
    config = load_config()
    hardware, benchmark = MODULE.validate_config(config)

    proposal = MODULE.build_proposal(
        config,
        hardware,
        benchmark,
        CONFIG,
    )

    json_path = tmp_path / "hpc-benchmark-proposal.json"
    markdown_path = tmp_path / "hpc-benchmark-proposal.md"

    json_content = (
        json.dumps(
            proposal,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    markdown_content = MODULE.build_markdown(proposal)

    MODULE.write_atomic(json_path, json_content)
    MODULE.write_atomic(markdown_path, markdown_content)

    assert json_path.is_file()
    assert markdown_path.is_file()

    saved_json = json.loads(json_path.read_text(encoding="utf-8"))
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert saved_json["benchmark"]["parallelism_target"] == 664
    assert saved_json["benchmark"]["maximum_target_dimension"] == 10_000_000
    assert saved_json["status"] == "PROPOSED_NOT_EXECUTED"

    assert "664" in saved_markdown
    assert "10,000,000" in saved_markdown


def test_main_generates_both_required_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "reports"

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_hpc_benchmark_proposal.py",
            "--config",
            str(CONFIG),
            "--output-dir",
            str(output_dir),
        ],
    )

    result = MODULE.main()

    json_path = output_dir / "hpc-benchmark-proposal.json"
    markdown_path = output_dir / "hpc-benchmark-proposal.md"

    assert result == 0
    assert json_path.is_file()
    assert markdown_path.is_file()

    generated = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert generated["status"] == "PROPOSED_NOT_EXECUTED"
    assert generated["benchmark"]["parallelism_target"] == 664
    assert generated["benchmark"]["maximum_target_dimension"] == 10_000_000
    assert "PROPOSED — NOT EXECUTED" in markdown


def test_main_does_not_modify_source_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "hpc-target.json"
    original = valid_config()

    source.write_text(
        json.dumps(original, indent=2) + "\n",
        encoding="utf-8",
    )
    before = source.read_bytes()

    output_dir = tmp_path / "reports"

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_hpc_benchmark_proposal.py",
            "--config",
            str(source),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert MODULE.main() == 0
    assert source.read_bytes() == before


def test_main_rejects_missing_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = tmp_path / "missing-hpc-target.json"
    output_dir = tmp_path / "reports"

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_hpc_benchmark_proposal.py",
            "--config",
            str(missing),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert MODULE.main() == 2
    assert not output_dir.exists()


def test_source_configuration_is_not_mutated_by_validation() -> None:
    config = load_config()
    original = copy.deepcopy(config)

    MODULE.validate_config(config)

    assert config == original
