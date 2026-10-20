"""Fail-closed verification of the complete P2 evidence package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

P2_ROOT = Path(__file__).resolve().parents[1]

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_FILES = {
    "reports/reference_config.json",
    "reports/environment_report.json",
    "reports/pytest-run.json",
    "reports/junit.xml",
    "reports/artifact_validation.json",
    "reports/numerical_validation.json",
    "reports/pennylane_parity.json",
    "artifacts/state_vector.csv",
    "artifacts/probabilities.csv",
    "artifacts/density_matrix.csv",
    "artifacts/reduced_density_q4.csv",
    "artifacts/reduced_density_q123.csv",
    "artifacts/metadata.json",
    "MANIFEST.txt",
    "SHA256SUMS.txt",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict:
    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return data


def validate_status_report(
    path: Path,
    errors: list[str],
) -> None:
    try:
        report = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot read report {path}: {exc}")
        return

    if report.get("status") != "PASS":
        errors.append(f"Report is not PASS: {path}")

    if report.get("all_checks_pass") is not True:
        errors.append(f"Report all_checks_pass is not true: {path}")


def validate_inventory(
    root: Path,
    errors: list[str],
) -> tuple[int, int]:
    manifest_path = root / "MANIFEST.txt"
    sums_path = root / "SHA256SUMS.txt"

    if not manifest_path.is_file():
        errors.append("MANIFEST.txt is missing.")
        return 0, 0

    if not sums_path.is_file():
        errors.append("SHA256SUMS.txt is missing.")
        return 0, 0

    try:
        manifest_lines = [
            line.strip()
            for line in manifest_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip() and not line.startswith("#")
        ]

        checksum_lines = [
            line.strip()
            for line in sums_path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip() and not line.startswith("#")
        ]

    except (OSError, UnicodeError) as exc:
        errors.append(f"Cannot read inventory: {exc}")
        return 0, 0

    if len(manifest_lines) != len(set(manifest_lines)):
        errors.append("MANIFEST.txt contains duplicate paths.")

    if len(checksum_lines) != len(set(checksum_lines)):
        errors.append("SHA256SUMS.txt contains duplicate entries.")

    checksum_map: dict[str, str] = {}

    for number, line in enumerate(checksum_lines, start=1):
        parts = line.split("  ", 1)

        if len(parts) != 2:
            errors.append(
                f"SHA256SUMS line {number}: invalid format."
            )
            continue

        digest, relative = parts

        if not HASH_PATTERN.fullmatch(digest):
            errors.append(
                f"SHA256SUMS line {number}: invalid digest."
            )
            continue

        if relative in checksum_map:
            errors.append(
                f"SHA256SUMS duplicate path: {relative}"
            )
            continue

        checksum_map[relative] = digest

    manifest_set = set(manifest_lines)
    checksum_set = set(checksum_map)

    if manifest_set != checksum_set:
        missing_hashes = sorted(manifest_set - checksum_set)
        extra_hashes = sorted(checksum_set - manifest_set)

        if missing_hashes:
            errors.append(
                "Missing checksum entries: "
                + ", ".join(missing_hashes)
            )

        if extra_hashes:
            errors.append(
                "Unexpected checksum entries: "
                + ", ".join(extra_hashes)
            )

    for relative, expected_hash in checksum_map.items():
        candidate = root / relative

        if candidate.is_absolute() is False:
            errors.append(
                f"Invalid checksum path: {relative}"
            )
            continue

        if ".." in Path(relative).parts or "\\" in relative:
            errors.append(
                f"Unsafe checksum path: {relative}"
            )
            continue

        if not candidate.is_file() or candidate.is_symlink():
            errors.append(
                f"Checksum target missing or unsafe: {relative}"
            )
            continue

        try:
            actual_hash = sha256_file(candidate)
        except OSError as exc:
            errors.append(
                f"Cannot hash {relative}: {exc}"
            )
            continue

        if actual_hash != expected_hash:
            errors.append(
                f"SHA-256 mismatch: {relative}"
            )

    return len(manifest_set), len(checksum_map)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the final P2 reproducibility package."
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=P2_ROOT,
    )

    args = parser.parse_args()
    root = args.root.resolve()

    errors: list[str] = []

    if not root.is_dir():
        print("FAIL: P2 root does not exist.")
        return 2

    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            errors.append(
                f"Required file missing: {relative}"
            )

    for relative in (
        "reports/artifact_validation.json",
        "reports/numerical_validation.json",
        "reports/pennylane_parity.json",
    ):
        path = root / relative

        if path.is_file():
            validate_status_report(
                path,
                errors,
            )

    try:
        pytest_report = load_json(
            root / "reports" / "pytest-run.json"
        )

        if pytest_report.get("exit_code") != 0:
            errors.append("Pytest exit code is not zero.")

        if pytest_report.get("status") != "PASS":
            errors.append("Pytest report status is not PASS.")

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid pytest report: {exc}")

    manifest_count, checksum_count = validate_inventory(
        root,
        errors,
    )

    benchmark_json = (
        root / "benchmarks" / "results" / "benchmark_report.json"
    )

    if benchmark_json.is_file():
        try:
            from validate_benchmark import validate_results

            benchmark_errors = validate_results(
                benchmark_json.parent
            )

            errors.extend(
                "Benchmark: " + error
                for error in benchmark_errors
            )

        except (ImportError, OSError, ValueError) as exc:
            errors.append(
                f"Cannot validate optional benchmark: {exc}"
            )

    verdict = (
        "P2_ACCEPTED"
        if not errors
        else "P2_REJECTED"
    )

    print("=" * 72)
    print("P2 FINAL PACKAGE VERIFICATION")
    print("Manifest entries:", manifest_count)
    print("Checksum entries:", checksum_count)
    print("Errors:", len(errors))

    for error in errors:
        print("FAIL:", error)

    print("VERDICT:", verdict)

    return 0 if verdict == "P2_ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
