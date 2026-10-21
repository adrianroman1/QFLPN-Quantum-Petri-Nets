#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "audit"

ORIGINAL_PATH = AUDIT_DIR / "validate_benchmark.original.py"
MIGRATED_PATH = ROOT / "P2/benchmarks/validate_benchmark.py"
CONFIG_PATH = ROOT / "P2/benchmarks/benchmark_config.json"

ORIGINAL_GIT_PATH = "P2/benchmarks/validate_benchmark.py"

ORIGINAL_FILENAMES = {
    "json": "benchmark_report.json",
    "csv": "benchmark_results.csv",
    "markdown": "BENCHMARK_RESULTS.md",
    "environment": "environment.txt",
}

REPORT_PATH = AUDIT_DIR / "behavior_report.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_module(
    path: Path,
    module_name: str,
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Cannot import module: {path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    return module


def git_blob_sha(path: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (
        OSError,
        subprocess.CalledProcessError,
    ):
        return None


def normalize_errors(
    errors: list[str],
    replacements: dict[str, str],
) -> list[str]:
    result = []

    for error in errors:
        value = str(error)

        for old, new in replacements.items():
            value = value.replace(old, new)

        result.append(value)

    return result


def build_error_diff(
    original: list[str],
    migrated: list[str],
) -> list[dict]:
    differences = []

    max_length = max(
        len(original),
        len(migrated),
    )

    for index in range(max_length):
        old = (
            original[index]
            if index < len(original)
            else None
        )

        new = (
            migrated[index]
            if index < len(migrated)
            else None
        )

        if old != new:
            differences.append({
                "index": index,
                "original": old,
                "migrated": new,
            })

    return differences


def main() -> int:
    report = {
        "original_git_sha": git_blob_sha(
            ORIGINAL_GIT_PATH
        ),
        "original_sha256": None,
        "migrated_sha256": None,
        "artifact_hashes": {},
        "original_verdict": "NOT_RUN",
        "migrated_verdict": "NOT_RUN",
        "original_error_count": None,
        "migrated_error_count": None,
        "original_errors": [],
        "migrated_errors": [],
        "error_diff": [],
        "equivalent": False,
        "passed": False,
    }

    try:
        if not ORIGINAL_PATH.is_file():
            raise FileNotFoundError(
                f"Original validator missing: {ORIGINAL_PATH}"
            )

        if not MIGRATED_PATH.is_file():
            raise FileNotFoundError(
                f"Migrated validator missing: {MIGRATED_PATH}"
            )

        if not CONFIG_PATH.is_file():
            raise FileNotFoundError(
                f"Configuration missing: {CONFIG_PATH}"
            )

        report["original_sha256"] = sha256_file(
            ORIGINAL_PATH
        )

        report["migrated_sha256"] = sha256_file(
            MIGRATED_PATH
        )

        benchmark_dir = str(
            MIGRATED_PATH.parent
        )

        if benchmark_dir not in sys.path:
            sys.path.insert(0, benchmark_dir)

        contract_module = load_module(
            MIGRATED_PATH.parent / "benchmark_contract.py",
            "benchmark_contract",
        )

        migrated_module = load_module(
            MIGRATED_PATH,
            "p2_migrated_validate_benchmark",
        )

        original_module = load_module(
            ORIGINAL_PATH,
            "p2_original_validate_benchmark",
        )

        contract = (
            contract_module.load_benchmark_contract(
                CONFIG_PATH
            )
        )

        if not isinstance(
            contract.artifact_paths,
            dict,
        ):
            raise TypeError(
                "contract.artifact_paths must be a dictionary"
            )

        missing = [
            key
            for key in ORIGINAL_FILENAMES
            if key not in contract.artifact_paths
        ]

        if missing:
            raise ValueError(
                f"Missing configured artifact keys: {missing}"
            )

        artifact_hashes = {}

        for key, path in contract.artifact_paths.items():
            artifact_path = Path(path)

            if artifact_path.is_file():
                artifact_hashes[key] = sha256_file(
                    artifact_path
                )
            else:
                artifact_hashes[key] = None

        report["artifact_hashes"] = artifact_hashes

        missing_artifacts = [
            key
            for key in ORIGINAL_FILENAMES
            if artifact_hashes.get(key) is None
        ]

        if missing_artifacts:
            raise FileNotFoundError(
                "Missing configured artifacts: "
                f"{missing_artifacts}"
            )

        with tempfile.TemporaryDirectory(
            prefix="p2_original_validator_"
        ) as temporary:

            original_input_dir = Path(temporary)

            for key, historical_name in (
                ORIGINAL_FILENAMES.items()
            ):
                source = Path(
                    contract.artifact_paths[key]
                )

                destination = (
                    original_input_dir / historical_name
                )

                shutil.copy2(
                    source,
                    destination,
                )

            original_errors = (
                original_module.validate_results(
                    original_input_dir
                )
            )

            migrated_errors = (
                migrated_module.validate_results(
                    contract
                )
            )

            if not isinstance(original_errors, list):
                raise TypeError(
                    "Original validator must return a list"
                )

            if not isinstance(migrated_errors, list):
                raise TypeError(
                    "Migrated validator must return a list"
                )

            replacements = {
                str(original_input_dir):
                    "<BENCHMARK_OUTPUT>",
                str(contract.output_directory):
                    "<BENCHMARK_OUTPUT>",
            }

            original_normalized = normalize_errors(
                original_errors,
                replacements,
            )

            migrated_normalized = normalize_errors(
                migrated_errors,
                replacements,
            )

            report["original_errors"] = (
                original_normalized
            )

            report["migrated_errors"] = (
                migrated_normalized
            )

            report["original_error_count"] = len(
                original_errors
            )

            report["migrated_error_count"] = len(
                migrated_errors
            )

            report["original_verdict"] = (
                "BENCHMARK_ACCEPTED"
                if not original_errors
                else "BENCHMARK_REJECTED"
            )

            report["migrated_verdict"] = (
                "BENCHMARK_ACCEPTED"
                if not migrated_errors
                else "BENCHMARK_REJECTED"
            )

            report["error_diff"] = build_error_diff(
                original_normalized,
                migrated_normalized,
            )

            equivalent = (
                report["original_verdict"]
                == report["migrated_verdict"]
                and original_normalized
                == migrated_normalized
                and report["original_error_count"]
                == report["migrated_error_count"]
            )

            report["equivalent"] = equivalent
            report["passed"] = equivalent

    except Exception as exc:
        report["execution_error"] = (
            f"{type(exc).__name__}: {exc}"
        )

        report["equivalent"] = False
        report["passed"] = False

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

    print(
        "\nBEHAVIOR REVIEW:",
        "PASS" if report["passed"] else "FAIL",
    )

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
