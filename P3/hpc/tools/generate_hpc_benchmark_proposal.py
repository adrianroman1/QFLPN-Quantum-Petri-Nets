#!/usr/bin/env python3
"""Generate the QFLPN P3 proposed HPC SpMV benchmark report.

Source:
    P3/hpc/config/hpc-target.json

Outputs:
    P3/hpc/reports/hpc-benchmark-proposal.json
    P3/hpc/reports/hpc-benchmark-proposal.md

The generated report describes a proposed configuration only. It does not
execute benchmarks, invent measurements, or claim that 664 workers or
dimension 10,000,000 have been tested.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CONFIG_SCHEMA = "qflpn-p3-hpc-target-v2"
PROPOSAL_SCHEMA = "qflpn-p3-hpc-benchmark-proposal-v1"

DEFAULT_CONFIG = Path("P3/hpc/config/hpc-target.json")
DEFAULT_OUTPUT_DIR = Path("P3/hpc/reports")


class ProposalError(ValueError):
    """Raised when the target configuration is invalid."""


def load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProposalError(f"Configuration file not found: {path}") from exc
    except OSError as exc:
        raise ProposalError(f"Cannot read configuration {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProposalError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ProposalError("The configuration root must be a JSON object.")

    if config.get("schema") != CONFIG_SCHEMA:
        raise ProposalError(
            f"Unsupported configuration schema: {config.get('schema')!r}; "
            f"expected {CONFIG_SCHEMA!r}."
        )

    if config.get("status") != "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE":
        raise ProposalError(
            "The configuration must retain the explicit "
            "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE status."
        )

    return config


def require_int(
    value: Any,
    field: str,
    *,
    minimum: int = 1,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ProposalError(f"{field} must be an integer >= {minimum}.")
    return value


def validate_config(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    hardware = config.get("hardware_target")
    benchmark = config.get("benchmark")

    if not isinstance(hardware, dict):
        raise ProposalError("hardware_target must be a JSON object.")
    if not isinstance(benchmark, dict):
        raise ProposalError("benchmark must be a JSON object.")

    compute_nodes = require_int(
        hardware.get("compute_nodes"), "hardware_target.compute_nodes"
    )
    physical_cores = require_int(
        hardware.get("physical_cores_total"),
        "hardware_target.physical_cores_total",
    )
    ram_total = require_int(
        hardware.get("ram_gib_total"), "hardware_target.ram_gib_total"
    )
    ram_per_node = require_int(
        hardware.get("ram_gib_per_node"),
        "hardware_target.ram_gib_per_node",
    )

    groups = hardware.get("node_groups")
    if not isinstance(groups, list) or not groups:
        raise ProposalError("hardware_target.node_groups must be a non-empty list.")

    group_nodes = 0
    group_cores = 0
    normalized_groups: list[dict[str, Any]] = []

    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ProposalError(f"node_groups[{index}] must be an object.")

        names = group.get("names")
        nodes = require_int(group.get("nodes"), f"node_groups[{index}].nodes")
        cores = require_int(
            group.get("physical_cores_per_node"),
            f"node_groups[{index}].physical_cores_per_node",
        )

        if not isinstance(names, str) or not names.strip():
            raise ProposalError(f"node_groups[{index}].names must be non-empty.")

        group_nodes += nodes
        group_cores += nodes * cores

        normalized_groups.append({
            "names": names,
            "nodes": nodes,
            "physical_cores_per_node": cores,
            "group_physical_cores": nodes * cores,
        })

    if group_nodes != compute_nodes:
        raise ProposalError(
            f"Node groups total {group_nodes}; target declares {compute_nodes}."
        )

    if group_cores != physical_cores:
        raise ProposalError(
            f"Node groups total {group_cores} physical cores; "
            f"target declares {physical_cores}."
        )

    if compute_nodes * ram_per_node != ram_total:
        raise ProposalError(
            "RAM consistency failed: compute_nodes × ram_gib_per_node "
            "must equal ram_gib_total."
        )

    motherboard = hardware.get("motherboard")
    if not isinstance(motherboard, dict):
        raise ProposalError("hardware_target.motherboard must be an object.")

    motherboard_fields = motherboard.get("fields")
    if motherboard.get("collection_required") is not True:
        raise ProposalError("Motherboard collection must be required.")

    if motherboard_fields != ["manufacturer", "model", "version"]:
        raise ProposalError(
            "Motherboard fields must be manufacturer, model and version."
        )

    if motherboard.get("missing_value") != "UNAVAILABLE":
        raise ProposalError(
            "Motherboard missing_value must be UNAVAILABLE."
        )

    workload = benchmark.get("workload")
    parallelism = require_int(
        benchmark.get("parallelism_target"),
        "benchmark.parallelism_target",
    )

    worker_counts = benchmark.get("worker_counts")
    thresholds = benchmark.get("thresholds")

    if not isinstance(worker_counts, list) or not worker_counts:
        raise ProposalError("benchmark.worker_counts must be a non-empty list.")

    if not isinstance(thresholds, list) or not thresholds:
        raise ProposalError("benchmark.thresholds must be a non-empty list.")

    for index, value in enumerate(worker_counts):
        require_int(value, f"benchmark.worker_counts[{index}]")

    for index, value in enumerate(thresholds):
        require_int(value, f"benchmark.thresholds[{index}]")

    if worker_counts != sorted(set(worker_counts)):
        raise ProposalError(
            "benchmark.worker_counts must be strictly increasing and unique."
        )

    if thresholds != sorted(set(thresholds)):
        raise ProposalError(
            "benchmark.thresholds must be strictly increasing and unique."
        )

    if workload != "SpMV":
        raise ProposalError("The proposed workload must be SpMV.")

    if parallelism != physical_cores:
        raise ProposalError(
            "benchmark.parallelism_target must equal physical_cores_total."
        )

    if parallelism not in worker_counts:
        raise ProposalError(
            "worker_counts must include the maximum parallelism target."
        )

    maximum_dimension = require_int(
        benchmark.get("maximum_target_dimension"),
        "benchmark.maximum_target_dimension",
    )

    if maximum_dimension != 10_000_000:
        raise ProposalError(
            "The maximum target dimension must be 10,000,000."
        )

    if maximum_dimension not in thresholds:
        raise ProposalError(
            "benchmark.thresholds must include maximum_target_dimension."
        )

    warmup = require_int(
        benchmark.get("minimum_warmup"),
        "benchmark.minimum_warmup",
    )
    measurements = require_int(
        benchmark.get("minimum_valid_measurements"),
        "benchmark.minimum_valid_measurements",
    )

    if warmup < 5:
        raise ProposalError("minimum_warmup must be at least 5.")

    if measurements < 30:
        raise ProposalError(
            "minimum_valid_measurements must be at least 30."
        )

    if benchmark.get("execution_status") != "NOT_EXECUTED":
        raise ProposalError(
            "Proposal generation requires execution_status=NOT_EXECUTED. "
            "Measured results must be reported separately."
        )

    hardware_summary = {
        "compute_nodes": compute_nodes,
        "physical_cores_total": physical_cores,
        "ram_gib_total": ram_total,
        "ram_gib_per_node": ram_per_node,
        "node_groups": normalized_groups,
        "motherboard": {
            "collection_required": True,
            "collection_scope": "EACH_COMPUTE_NODE",
            "fields": motherboard_fields,
            "source": motherboard.get("source"),
            "missing_value": motherboard.get("missing_value"),
        },
        "management_node": config.get("management_node"),
    }

    benchmark_summary = {
        "workload": workload,
        "parallelism_target": parallelism,
        "worker_counts": worker_counts,
        "thresholds": thresholds,
        "maximum_target_dimension": maximum_dimension,
        "minimum_warmup": warmup,
        "minimum_valid_measurements": measurements,
        "execution_status": "NOT_EXECUTED",
    }

    return hardware_summary, benchmark_summary


def build_proposal(
    config: dict[str, Any],
    hardware: dict[str, Any],
    benchmark: dict[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    return {
        "schema": PROPOSAL_SCHEMA,
        "schema_version": "1.0.0",
        "status": "PROPOSED_NOT_EXECUTED",
        "evidence_classification": "CONFIGURATION_ONLY_NOT_PERFORMANCE_EVIDENCE",
        "source_configuration": str(config_path),
        "source_configuration_schema": config["schema"],
        "hardware_target": hardware,
        "benchmark": benchmark,
        "execution_evidence": {
            "benchmark_executed": False,
            "664_worker_execution_demonstrated": False,
            "dimension_10000000_execution_demonstrated": False,
            "measured_performance_claims": False,
        },
        "integrity_scope": {
            "must_be_included_in_manifest": "P3/MANIFEST.txt",
            "must_be_included_in_checksums": "P3/SHA256SUMS.txt",
            "workflow_job": "p3_validation",
        },
    }


def markdown_table(rows: list[tuple[str, Any]]) -> str:
    lines = [
        "| Parameter | Proposed value |",
        "|---|---:|",
    ]
    for label, value in rows:
        lines.append(f"| {label} | {value} |")
    return "\n".join(lines)


def build_markdown(proposal: dict[str, Any]) -> str:
    hardware = proposal["hardware_target"]
    benchmark = proposal["benchmark"]
    motherboard = hardware["motherboard"]

    hardware_rows = [
        ("Compute nodes", hardware["compute_nodes"]),
        ("Physical CPU cores", hardware["physical_cores_total"]),
        ("Total RAM", f'{hardware["ram_gib_total"]:,} GiB'),
        ("RAM per node", f'{hardware["ram_gib_per_node"]:,} GiB'),
    ]

    benchmark_rows = [
        ("Workload", benchmark["workload"]),
        ("Target parallelism", benchmark["parallelism_target"]),
        ("Maximum target dimension", f'{benchmark["maximum_target_dimension"]:,}'),
        ("Minimum warm-up", benchmark["minimum_warmup"]),
        ("Minimum valid measurements", benchmark["minimum_valid_measurements"]),
        ("Execution status", benchmark["execution_status"]),
    ]

    lines = [
        "# QFLPN P3 — HPC Benchmark Proposal",
        "",
        "> **PROPOSED — NOT EXECUTED.** This document describes the target",
        "> configuration only. It contains no measured performance results.",
        "",
        "## 1. Hardware target",
        "",
        markdown_table(hardware_rows),
        "",
        "### Compute-node topology",
        "",
        "| Node group | Nodes | Physical cores per node | Group core total |",
        "|---|---:|---:|---:|",
    ]

    for group in hardware["node_groups"]:
        lines.append(
            f'| {group["names"]} | {group["nodes"]} | '
            f'{group["physical_cores_per_node"]} | '
            f'{group["group_physical_cores"]} |'
        )

    lines.extend([
        "",
        f'**Total: {hardware["compute_nodes"]} nodes and '
        f'{hardware["physical_cores_total"]} physical cores.**',
        "",
        "### Motherboard inventory requirements",
        "",
        f'- Collection required: **{motherboard["collection_required"]}**',
        f'- Collection scope: **{motherboard["collection_scope"]}**',
        f'- Fields: {", ".join(motherboard["fields"])}',
        f'- Source: `{motherboard["source"]}`',
        f'- Missing values: `{motherboard["missing_value"]}`',
        "",
        "Motherboard values must be collected from each compute node. "
        "The proposal does not invent manufacturer or model values.",
        "",
        "## 2. SpMV benchmark proposal",
        "",
        markdown_table(benchmark_rows),
        "",
        "### Worker-count campaign",
        "",
        "`" + " · ".join(str(value) for value in benchmark["worker_counts"]) + "`",
        "",
        "### Matrix-dimension thresholds",
        "",
        "`" + " · ".join(
            f"{value:,}" for value in benchmark["thresholds"]
        ) + "`",
        "",
        "The maximum target dimension is **10,000,000**. This is a proposed",
        "campaign point, not a measured or validated execution.",
        "",
        "## 3. Evidence classification",
        "",
        "- Configuration status: `PROPOSED_NOT_EXECUTED`",
        "- Benchmark execution: `NOT_EXECUTED`",
        "- 664-worker execution demonstrated: `false`",
        "- Dimension 10,000,000 execution demonstrated: `false`",
        "- Measured performance claims: `false`",
        "",
        "The proposal must not be interpreted as proof of distributed MPI",
        "execution, 664-core scaling, or measured SpMV performance.",
        "",
        "## 4. Validation and integrity",
        "",
        "- Workflow job: `p3_validation`",
        "- Global manifest: `P3/MANIFEST.txt`",
        "- SHA-256 inventory: `P3/SHA256SUMS.txt`",
        "- Source configuration: `" + proposal["source_configuration"] + "`",
        "",
        "---",
        "",
        "Generated automatically from `hpc-target.json`.",
        "",
    ])

    return "\n".join(lines)


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        config = load_config(args.config)
        hardware, benchmark = validate_config(config)

        proposal = build_proposal(
            config,
            hardware,
            benchmark,
            args.config,
        )

        json_path = args.output_dir / "hpc-benchmark-proposal.json"
        markdown_path = args.output_dir / "hpc-benchmark-proposal.md"

        json_content = (
            json.dumps(
                proposal,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        )

        markdown_content = build_markdown(proposal)

        write_atomic(json_path, json_content)
        write_atomic(markdown_path, markdown_content)

        print(f"HPC_PROPOSAL_JSON={json_path}")
        print(f"HPC_PROPOSAL_MARKDOWN={markdown_path}")
        print("HPC_PROPOSAL_STATUS=PROPOSED_NOT_EXECUTED")
        print("HPC_PROPOSAL_SOURCE=hpc-target.json")
        print("HPC_PROPOSAL_PARALLELISM=664")
        print("HPC_PROPOSAL_MAXIMUM_DIMENSION=10000000")

        return 0

    except ProposalError as exc:
        print(f"HPC_PROPOSAL_INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"HPC_PROPOSAL_OUTPUT_ERROR: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(
            f"HPC_PROPOSAL_RUNTIME_ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
