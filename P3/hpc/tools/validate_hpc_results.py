#!/usr/bin/env python3
"""
Fail-closed validator for QFLPN P3 distributed HPC benchmark results.

CSV contract:
    run_id,commit,configuration_id,workload,strategy,n,nnz,workers,
    mpi_ranks,node_count,threshold,fork_id,iteration,elapsed_time_ms,
    status,correctness_pass,max_abs_error,max_rel_error

JSON metadata contract:
    {
      "schema": "qflpn-p3-hpc-benchmark",
      "schema_version": "1.0.0",
      "run_id": "...",
      "source_commit": "<40 hexadecimal characters>",
      "configuration_id": "P3-HPC-664-REFERENCE",
      "node_count": 16,
      "mpi_ranks": 664,
      "benchmark_csv": "benchmark.csv"
    }

The CSV is the raw observation source. The JSON is its provenance/summary
metadata. The validator never infers missing measurements and never turns an
unexecuted HPC campaign into PASS.

Example:
    python3 P3/hpc/tools/validate_hpc_results.py \
        --config P3/hpc/config/hpc-664.json \
        --inventory P3/results/hpc/inventory/node_inventory.json \
        --benchmark-csv P3/results/hpc/raw/benchmark.csv \
        --benchmark-json P3/results/hpc/raw/benchmark.json \
        --output P3/results/hpc/reports/HPC_VALIDATION.json

Exit codes:
    0: HPC result package passed this validator
    2: invalid arguments/configuration
    3: validation failed or campaign is not evaluable
    4: unexpected runtime failure

Only Python's standard library is used.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SCHEMA = "qflpn-p3-hpc-validation"
SCHEMA_VERSION = "1.0.0"

REQUIRED_CSV_COLUMNS = {
    "run_id",
    "commit",
    "configuration_id",
    "workload",
    "strategy",
    "n",
    "nnz",
    "workers",
    "mpi_ranks",
    "node_count",
    "threshold",
    "fork_id",
    "iteration",
    "elapsed_time_ms",
    "status",
    "correctness_pass",
    "max_abs_error",
    "max_rel_error",
}

REQUIRED_JSON_FIELDS = {
    "schema",
    "schema_version",
    "run_id",
    "source_commit",
    "configuration_id",
    "node_count",
    "mpi_ranks",
    "benchmark_csv",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Lipsește {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalid pentru {label}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError(f"{label} trebuie să aibă un obiect JSON la rădăcină.")
    return value


def add_error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def parse_int(value: Any, field: str, row_number: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Linia CSV {row_number}: {field} nu este întreg.") from exc
    return parsed


def parse_float(value: Any, field: str, row_number: int) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Linia CSV {row_number}: {field} nu este numeric.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Linia CSV {row_number}: {field} nu este finit.")
    return parsed


def parse_bool(value: Any, field: str, row_number: int) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(
        f"Linia CSV {row_number}: {field} trebuie să fie true/false."
    )


def validate_inventory(
    config: dict[str, Any],
    inventory: dict[str, Any],
    metadata: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    if inventory.get("schema") != "qflpn-p3-hpc-inventory":
        add_error(errors, "INVENTORY_SCHEMA_INVALID", "Schema inventarului este invalidă.")
        return

    validation = inventory.get("validation", {})
    if validation.get("status") != "PASS_LOCAL_PREFLIGHT":
        add_error(
            errors,
            "INVENTORY_PREFLIGHT_NOT_PASSED",
            "Inventarul nu are status PASS_LOCAL_PREFLIGHT.",
        )

    if validation.get("errors"):
        add_error(
            errors,
            "INVENTORY_CONTAINS_ERRORS",
            "Inventarul conține erori de preflight.",
        )

    slurm = inventory.get("scheduler", {}).get("slurm", {})
    if not slurm.get("active"):
        add_error(
            errors,
            "SLURM_ALLOCATION_ABSENT",
            "Inventarul nu demonstrează o alocare Slurm activă.",
        )

    expected_nodes = config.get("hardware_reference", {}).get("compute_nodes")
    observed_nodes_raw = slurm.get("environment", {}).get("SLURM_NNODES")
    try:
        observed_nodes = int(observed_nodes_raw)
    except (TypeError, ValueError):
        observed_nodes = None

    if observed_nodes is None:
        add_error(
            errors,
            "SLURM_NODE_COUNT_UNKNOWN",
            "SLURM_NNODES lipsește sau nu este numeric.",
        )
    elif observed_nodes != expected_nodes:
        add_error(
            errors,
            "SLURM_NODE_COUNT_MISMATCH",
            f"Slurm a alocat {observed_nodes} noduri; configurația cere {expected_nodes}.",
        )

    metadata_nodes = metadata.get("node_count")
    if metadata_nodes != expected_nodes:
        add_error(
            errors,
            "BENCHMARK_NODE_COUNT_MISMATCH",
            "Numărul de noduri din metadata nu corespunde configurației HPC.",
        )

    if observed_nodes is not None and metadata_nodes != observed_nodes:
        add_error(
            errors,
            "INVENTORY_BENCHMARK_NODE_COUNT_MISMATCH",
            "Numărul de noduri din inventar și benchmark nu coincide.",
        )


def validate_metadata(
    config: dict[str, Any],
    metadata: dict[str, Any],
    errors: list[dict[str, str]],
) -> tuple[str | None, str | None]:
    missing = sorted(REQUIRED_JSON_FIELDS - set(metadata))
    if missing:
        add_error(
            errors,
            "BENCHMARK_METADATA_FIELDS_MISSING",
            "Lipsesc câmpuri obligatorii din benchmark JSON: " + ", ".join(missing),
        )

    if metadata.get("schema") != "qflpn-p3-hpc-benchmark":
        add_error(
            errors,
            "BENCHMARK_JSON_SCHEMA_INVALID",
            "Schema benchmark JSON este invalidă.",
        )

    if metadata.get("schema_version") != "1.0.0":
        add_error(
            errors,
            "BENCHMARK_JSON_VERSION_UNSUPPORTED",
            "Versiunea benchmark JSON trebuie să fie 1.0.0.",
        )

    expected_id = config.get("configuration_id")
    if metadata.get("configuration_id") != expected_id:
        add_error(
            errors,
            "CONFIGURATION_ID_MISMATCH",
            "Identificatorul configurației din benchmark nu corespunde.",
        )

    run_id = metadata.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        add_error(errors, "RUN_ID_MISSING", "run_id lipsește din metadata.")
        run_id = None

    commit = metadata.get("source_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        add_error(
            errors,
            "SOURCE_COMMIT_INVALID",
            "source_commit trebuie să fie un SHA Git complet de 40 de caractere.",
        )
        commit = None

    mpi_ranks = metadata.get("mpi_ranks")
    if not isinstance(mpi_ranks, int) or mpi_ranks <= 0:
        add_error(
            errors,
            "MPI_RANK_COUNT_INVALID",
            "mpi_ranks trebuie să fie un întreg pozitiv.",
        )

    return run_id, commit


def load_and_validate_csv(
    csv_path: Path,
    metadata: dict[str, Any],
    config: dict[str, Any],
    errors: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        handle = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        add_error(errors, "BENCHMARK_CSV_UNREADABLE", str(exc))
        return [], {"row_count": 0, "configuration_count": 0}

    observations: list[dict[str, Any]] = []

    with handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_CSV_COLUMNS - columns)

        if missing:
            add_error(
                errors,
                "BENCHMARK_CSV_COLUMNS_MISSING",
                "Lipsesc coloane CSV obligatorii: " + ", ".join(missing),
            )
            return [], {"row_count": 0, "configuration_count": 0}

        for row_number, raw in enumerate(reader, start=2):
            try:
                row: dict[str, Any] = dict(raw)

                for key in ("run_id", "commit", "configuration_id", "workload",
                            "strategy", "fork_id", "status"):
                    row[key] = str(row[key]).strip()

                for key in ("n", "nnz", "workers", "mpi_ranks",
                            "node_count", "threshold", "iteration"):
                    row[key] = parse_int(row[key], key, row_number)

                for key in ("elapsed_time_ms", "max_abs_error", "max_rel_error"):
                    row[key] = parse_float(row[key], key, row_number)

                row["correctness_pass"] = parse_bool(
                    row["correctness_pass"], "correctness_pass", row_number
                )

                if row["n"] <= 0 or row["nnz"] < 0:
                    raise ValueError(f"Linia CSV {row_number}: N/NNZ invalid.")
                if row["workers"] <= 0 or row["mpi_ranks"] <= 0 or row["node_count"] <= 0:
                    raise ValueError(f"Linia CSV {row_number}: resursele trebuie să fie pozitive.")
                if row["threshold"] <= 0 or row["iteration"] < 0:
                    raise ValueError(f"Linia CSV {row_number}: prag/iterație invalidă.")
                if row["elapsed_time_ms"] <= 0:
                    raise ValueError(f"Linia CSV {row_number}: timpul trebuie să fie pozitiv.")
                if row["max_abs_error"] < 0 or row["max_rel_error"] < 0:
                    raise ValueError(f"Linia CSV {row_number}: erorile nu pot fi negative.")
                if row["status"].upper() != "PASS":
                    raise ValueError(f"Linia CSV {row_number}: statusul nu este PASS.")
                if not row["correctness_pass"]:
                    raise ValueError(f"Linia CSV {row_number}: verificarea numerică a eșuat.")

                observations.append(row)

            except ValueError as exc:
                add_error(errors, "BENCHMARK_ROW_INVALID", str(exc))

    if not observations:
        add_error(
            errors,
            "BENCHMARK_HAS_NO_VALID_OBSERVATIONS",
            "CSV-ul nu conține nicio observație validă; datele absente nu pot trece.",
        )
        return [], {"row_count": 0, "configuration_count": 0}

    expected_run_id = metadata.get("run_id")
    expected_commit = metadata.get("source_commit")
    expected_config_id = config.get("configuration_id")

    for index, row in enumerate(observations, start=2):
        if row["run_id"] != expected_run_id:
            add_error(
                errors,
                "ROW_RUN_ID_MISMATCH",
                f"Observația {index}: run_id diferă de metadata.",
            )
        if row["commit"] != expected_commit:
            add_error(
                errors,
                "ROW_COMMIT_MISMATCH",
                f"Observația {index}: commit diferă de metadata.",
            )
        if row["configuration_id"] != expected_config_id:
            add_error(
                errors,
                "ROW_CONFIGURATION_MISMATCH",
                f"Observația {index}: configuration_id diferă de configurație.",
            )

        if row["node_count"] != metadata.get("node_count"):
            add_error(
                errors,
                "ROW_NODE_COUNT_MISMATCH",
                f"Observația {index}: node_count diferă de metadata.",
            )
        if row["mpi_ranks"] != metadata.get("mpi_ranks"):
            add_error(
                errors,
                "ROW_MPI_RANK_COUNT_MISMATCH",
                f"Observația {index}: mpi_ranks diferă de metadata.",
            )

    # A configuration is identified by workload, algorithm, problem size,
    # workers/ranks, threshold. Fork and iteration are repeated observations.
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        key = (
            row["workload"],
            row["strategy"],
            row["n"],
            row["nnz"],
            row["workers"],
            row["mpi_ranks"],
            row["node_count"],
            row["threshold"],
        )
        groups[key].append(row)

    minimum_forks = int(
        config.get("benchmark", {}).get("sampling", {}).get("minimum_forks", 5)
    )
    minimum_samples = int(
        config.get("benchmark", {}).get("sampling", {})
        .get("minimum_timed_samples_per_configuration", 30)
    )

    insufficient: list[dict[str, Any]] = []
    for key, rows in groups.items():
        forks: dict[str, int] = defaultdict(int)
        for row in rows:
            forks[row["fork_id"]] += 1

        if len(forks) < minimum_forks or len(rows) < minimum_samples:
            insufficient.append({
                "workload": key[0],
                "strategy": key[1],
                "n": key[2],
                "workers": key[4],
                "mpi_ranks": key[5],
                "threshold": key[7],
                "fork_count": len(forks),
                "sample_count": len(rows),
            })

    if insufficient:
        add_error(
            errors,
            "INSUFFICIENT_REPETITIONS",
            f"{len(insufficient)} configurații nu ating minimum "
            f"{minimum_forks} fork-uri și {minimum_samples} observații.",
        )

    return observations, {
        "row_count": len(observations),
        "configuration_count": len(groups),
        "minimum_forks_required": minimum_forks,
        "minimum_samples_required": minimum_samples,
        "insufficient_configurations": insufficient,
    }


def validate(
    config_path: Path,
    inventory_path: Path,
    csv_path: Path,
    json_path: Path,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []

    config = load_json(config_path, "configurația HPC")
    inventory = load_json(inventory_path, "inventarul hardware")
    metadata = load_json(json_path, "metadata benchmark")

    if config.get("schema") != "qflpn-p3-hpc-configuration":
        add_error(errors, "CONFIG_SCHEMA_INVALID", "Schema configurației HPC este invalidă.")

    run_id, commit = validate_metadata(config, metadata, errors)
    validate_inventory(config, inventory, metadata, errors)

    observations, csv_summary = load_and_validate_csv(
        csv_path, metadata, config, errors
    )

    if not observations:
        status = "NOT_EVALUATED" if not csv_path.exists() else "FAIL"
    else:
        status = "PASS" if not errors else "FAIL"

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "validated_at_utc": utc_now(),
        "configuration_id": config.get("configuration_id"),
        "run_id": run_id,
        "source_commit": commit,
        "status": status,
        "acceptance_effect": (
            "HPC_EVIDENCE_VALIDATED"
            if status == "PASS"
            else "P3_ACCEPTANCE_BLOCKED"
        ),
        "inputs": {
            "configuration": str(config_path),
            "inventory": str(inventory_path),
            "benchmark_csv": str(csv_path),
            "benchmark_json": str(json_path),
        },
        "observations": csv_summary,
        "errors": errors,
        "rules": {
            "fail_closed": True,
            "empty_data_can_pass": False,
            "same_run_id_required": True,
            "same_commit_required": True,
            "same_configuration_required": True,
            "minimum_forks_and_samples_enforced": True,
            "cluster_hardware_must_be_observed": True,
            "this_validator_does_not_generate_P3_ACCEPTED": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--benchmark-csv", required=True, type=Path)
    parser.add_argument("--benchmark-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        report = validate(
            args.config,
            args.inventory,
            args.benchmark_csv,
            args.benchmark_json,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(args.output)

        print(f"HPC_VALIDATION_REPORT={args.output}")
        print(f"HPC_VALIDATION_STATUS={report['status']}")
        print(f"HPC_ACCEPTANCE_EFFECT={report['acceptance_effect']}")

        return 0 if report["status"] == "PASS" else 3

    except ValueError as exc:
        print(f"VALIDATION_INPUT_ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"VALIDATION_RUNTIME_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
