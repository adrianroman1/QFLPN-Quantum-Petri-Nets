#!/usr/bin/env python3
"""
P2-BENCH-CONFIG-01
Behavioral Preservation Audit.

Compară:
- artefactele JSON;
- structura CSV;
- secțiunea Generated evidence din Markdown;
- artefactul de environment;
- verdictul validatorului original și migrat.

Baseline validator:
eb6f382fb70a1f04750b72931ef54f77eb28c470

IMPORTANT:
Nu declară echivalență numerică fără o execuție independentă
a ambelor versiuni pe aceleași intrări.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import traceback

from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = ROOT / "P2" / "benchmarks"

DEFAULT_CONFIG = (
    BENCHMARK_DIR / "benchmark_config.json"
)

VALIDATOR_PATH = (
    BENCHMARK_DIR / "validate_benchmark.py"
)

RUNNER_PATH = (
    BENCHMARK_DIR / "benchmark_runner.py"
)

VALIDATOR_BASELINE_BLOB = (
    "eb6f382fb70a1f04750b72931ef54f77eb28c470"
)

RUNNER_BASELINE_BLOB = (
    "03a63fec41a099944017d9c95d53c3b8656359a3"
)

REPORT_PATH = (
    ROOT / "audit" / "behavior_equivalence.json"
)

# Numele istorice sunt folosite EXCLUSIV pentru adapterul
# validatorului original, care nu cunoaște noul contract.
ORIGINAL_FILENAMES = {
    "json": "benchmark_report.json",
    "csv": "benchmark_results.csv",
    "markdown": "BENCHMARK_RESULTS.md",
    "environment": "environment.txt",
}


def git_blob(blob_sha: str) -> bytes:

    object_type = subprocess.run(
        [
            "git",
            "cat-file",
            "-t",
            blob_sha,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    if object_type != "blob":

        raise ValueError(
            f"Git object {blob_sha} is not a blob"
        )

    return subprocess.run(
        [
            "git",
            "cat-file",
            "blob",
            blob_sha,
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout


def load_module(
    path: Path,
    module_name: str,
):

    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:

        raise ImportError(
            f"Cannot load Python module: {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    return module


def sha256_file(path: Path) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def normalize_validator_result(value) -> list[str]:

    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]

    raise TypeError(
        "validate_results must return a list or tuple "
        f"of errors, not {type(value).__name__}"
    )


def compare_json_structure(
    original_path: Path,
    migrated_path: Path,
) -> dict:

    original = json.loads(
        original_path.read_text(
            encoding="utf-8"
        )
    )

    migrated = json.loads(
        migrated_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(original, dict):
        raise ValueError(
            "Original JSON root is not an object"
        )

    if not isinstance(migrated, dict):
        raise ValueError(
            "Migrated JSON root is not an object"
        )

    original_keys = set(original)
    migrated_keys = set(migrated)

    return {
        "status": (
            "PASS"
            if original_keys == migrated_keys
            else "FAIL"
        ),
        "original_keys": sorted(original_keys),
        "migrated_keys": sorted(migrated_keys),
        "missing_from_migrated": sorted(
            original_keys - migrated_keys
        ),
        "added_in_migrated": sorted(
            migrated_keys - original_keys
        ),
        "original_sha256": sha256_file(
            original_path
        ),
        "migrated_sha256": sha256_file(
            migrated_path
        ),
    }


def compare_csv_structure(
    original_path: Path,
    migrated_path: Path,
) -> dict:

    def read_csv(path: Path):

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            headers = reader.fieldnames

            if not headers:
                raise ValueError(
                    f"CSV has no header: {path}"
                )

            rows = list(reader)

            return headers, rows

    original_headers, original_rows = read_csv(
        original_path
    )

    migrated_headers, migrated_rows = read_csv(
        migrated_path
    )

    same_headers = (
        original_headers == migrated_headers
    )

    return {
        "status": (
            "PASS"
            if same_headers
            else "FAIL"
        ),
        "original_headers": original_headers,
        "migrated_headers": migrated_headers,
        "headers_identical": same_headers,
        "original_row_count": len(original_rows),
        "migrated_row_count": len(migrated_rows),
        "row_count_identical": (
            len(original_rows) == len(migrated_rows)
        ),
    }


def check_markdown(
    path: Path,
    configured_names: list[str],
) -> dict:

    content = path.read_text(
        encoding="utf-8"
    )

    has_evidence = (
        "Generated evidence" in content
    )

    missing_names = [
        name
        for name in configured_names
        if name not in content
    ]

    return {
        "status": (
            "PASS"
            if has_evidence and not missing_names
            else "FAIL"
        ),
        "generated_evidence_present": has_evidence,
        "configured_artifact_names": configured_names,
        "missing_artifact_names": missing_names,
    }


def check_environment(path: Path) -> dict:

    content = path.read_text(
        encoding="utf-8"
    )

    if not content.strip():

        return {
            "status": "FAIL",
            "reason": "Environment artifact is empty",
        }

    # Fișierul poate fi JSON sau text descriptiv.
    # Nu impunem artificial un format care nu este
    # declarat în contract.
    try:

        json.loads(content)

        detected_format = "json"

    except json.JSONDecodeError:

        detected_format = "text"

    return {
        "status": "PASS",
        "format": detected_format,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def prepare_original_artifact_adapter(
    artifact_paths: dict,
    temporary_directory: Path,
) -> Path:
    """
    Pregătește fișierele pentru validatorul original.

    API-ul original primește un director și caută numele
    istorice. Copierea se face numai în directorul temporar.
    """

    original_directory = (
        temporary_directory / "original_results"
    )

    original_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for artifact_key, historical_name in ORIGINAL_FILENAMES.items():

        source = Path(
            artifact_paths[artifact_key]
        )

        if not source.is_file():

            raise FileNotFoundError(
                f"Configured artifact missing: {source}"
            )

        shutil.copy2(
            source,
            original_directory / historical_name,
        )

    return original_directory


def compare_validator_results(
    contract,
    temporary_directory: Path,
) -> dict:

    baseline_bytes = git_blob(
        VALIDATOR_BASELINE_BLOB
    )

    baseline_path = (
        temporary_directory
        / "validate_benchmark_original.py"
    )

    baseline_path.write_bytes(
        baseline_bytes
    )

    original_module = load_module(
        baseline_path,
        "p2_behavior_original_validator",
    )

    migrated_module = load_module(
        VALIDATOR_PATH,
        "p2_behavior_migrated_validator",
    )

    original_directory = prepare_original_artifact_adapter(
        contract.artifact_paths,
        temporary_directory,
    )

    original_result = (
        original_module.validate_results(
            original_directory
        )
    )

    migrated_result = (
        migrated_module.validate_results(
            contract
        )
    )

    original_errors = normalize_validator_result(
        original_result
    )

    migrated_errors = normalize_validator_result(
        migrated_result
    )

    same_errors = (
        original_errors == migrated_errors
    )

    return {
        "status": (
            "PASS"
            if same_errors
            else "FAIL"
        ),
        "original_verdict": (
            "PASS"
            if not original_errors
            else "FAIL"
        ),
        "migrated_verdict": (
            "PASS"
            if not migrated_errors
            else "FAIL"
        ),
        "original_error_count": len(
            original_errors
        ),
        "migrated_error_count": len(
            migrated_errors
        ),
        "original_errors": original_errors,
        "migrated_errors": migrated_errors,
        "only_original": [
            error
            for error in original_errors
            if error not in migrated_errors
        ],
        "only_migrated": [
            error
            for error in migrated_errors
            if error not in original_errors
        ],
    }


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "P2-BENCH-CONFIG-01 behavioral preservation audit"
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help=(
            "Optional results directory. If supplied, "
            "it must match the configured output directory."
        ),
    )

    args = parser.parse_args()

    report = {
        "audit": "behavior_equivalence",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "NOT VERIFIED",
        "artifact_structure": {},
        "validator_compatibility": {
            "status": "NOT VERIFIED",
        },
        "runner_baseline": {
            "status": "NOT VERIFIED",
        },
        "numeric_equivalence": {
            "status": "NOT VERIFIED",
            "tolerance": 1e-12,
            "reason": (
                "A paired independent execution protocol for "
                "baseline and migrated benchmark has not been "
                "established by this script."
            ),
        },
        "issues": [],
    }

    try:

        sys.path.insert(
            0,
            str(BENCHMARK_DIR),
        )

        contract_module = load_module(
            BENCHMARK_DIR / "benchmark_contract.py",
            "p2_behavior_contract",
        )

        contract = (
            contract_module.load_benchmark_contract(
                args.config,
                p2_root=ROOT / "P2",
            )
        )

        if args.results is not None:

            expected_directory = Path(
                contract.output_directory
            ).resolve()

            supplied_directory = (
                args.results.resolve()
            )

            if supplied_directory != expected_directory:

                raise ValueError(
                    "--results does not match "
                    "contract.output_directory"
                )

        artifact_paths = {
            key: Path(value)
            for key, value in contract.artifact_paths.items()
        }

        required_keys = {
            "json",
            "csv",
            "markdown",
            "environment",
        }

        if set(artifact_paths) != required_keys:

            raise ValueError(
                "contract.artifact_paths does not contain "
                "exactly the four required artifact keys"
            )

        missing = [
            str(path)
            for path in artifact_paths.values()
            if not path.is_file()
        ]

        if missing:

            raise FileNotFoundError(
                "Missing benchmark artifacts: "
                + ", ".join(missing)
            )

        configured_names = [
            Path(str(value)).name
            for value in contract.artifacts.values()
        ]

        # -------------------------------------------------
        # JSON
        # -------------------------------------------------

        json_data = json.loads(
            artifact_paths["json"].read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(json_data, dict):

            raise ValueError(
                "Benchmark JSON root must be an object"
            )

        report["artifact_structure"]["json"] = {
            "status": "PASS",
            "keys": sorted(json_data),
            "sha256": sha256_file(
                artifact_paths["json"]
            ),
        }

        # -------------------------------------------------
        # CSV
        # -------------------------------------------------

        with artifact_paths["csv"].open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:

            reader = csv.DictReader(handle)

            if not reader.fieldnames:

                raise ValueError(
                    "Benchmark CSV has no columns"
                )

            rows = list(reader)

        report["artifact_structure"]["csv"] = {
            "status": "PASS",
            "columns": reader.fieldnames,
            "row_count": len(rows),
            "sha256": sha256_file(
                artifact_paths["csv"]
            ),
        }

        # -------------------------------------------------
        # Markdown
        # -------------------------------------------------

        report["artifact_structure"]["markdown"] = (
            check_markdown(
                artifact_paths["markdown"],
                configured_names,
            )
        )

        # -------------------------------------------------
        # Environment
        # -------------------------------------------------

        report["artifact_structure"]["environment"] = (
            check_environment(
                artifact_paths["environment"]
            )
        )

        # -------------------------------------------------
        # Validator comparison
        # -------------------------------------------------

        with tempfile.TemporaryDirectory(
            prefix="p2_behavior_audit_"
        ) as temporary_name:

            temporary_directory = Path(
                temporary_name
            )

            report["validator_compatibility"] = (
                compare_validator_results(
                    contract,
                    temporary_directory,
                )
            )

        # -------------------------------------------------
        # Runner source baseline
        # -------------------------------------------------

        original_runner = git_blob(
            RUNNER_BASELINE_BLOB
        )

        current_runner = RUNNER_PATH.read_bytes()

        same_runner = (
            hashlib.sha256(original_runner).digest()
            ==
            hashlib.sha256(current_runner).digest()
        )

        report["runner_baseline"] = {
            "status": (
                "PASS"
                if same_runner
                else "FAIL"
            ),
            "baseline_blob": RUNNER_BASELINE_BLOB,
            "baseline_sha256": hashlib.sha256(
                original_runner
            ).hexdigest(),
            "current_sha256": hashlib.sha256(
                current_runner
            ).hexdigest(),
            "unchanged": same_runner,
        }

        # -------------------------------------------------
        # Overall status
        # -------------------------------------------------

        component_statuses = [
            report["artifact_structure"]["json"]["status"],
            report["artifact_structure"]["csv"]["status"],
            report["artifact_structure"]["markdown"]["status"],
            report["artifact_structure"]["environment"]["status"],
            report["validator_compatibility"]["status"],
            report["runner_baseline"]["status"],
        ]

        if "FAIL" in component_statuses:

            report["status"] = "FAIL"

        elif (
            all(
                status == "PASS"
                for status in component_statuses
            )
            and report["numeric_equivalence"]["status"] == "PASS"
        ):

            report["status"] = "PASS"

        else:

            report["status"] = "NOT VERIFIED"

    except Exception as exc:

        report["issues"].append(
            f"{type(exc).__name__}: {exc}"
        )

        report["traceback"] = traceback.format_exc()

        if report["status"] != "FAIL":

            report["status"] = "NOT VERIFIED"

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    return (
        1
        if report["status"] == "FAIL"
        else 0
    )


if __name__ == "__main__":

    raise SystemExit(main())
