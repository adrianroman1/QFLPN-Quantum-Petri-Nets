#!/usr/bin/env bash
# P2-BENCH-CONFIG-01 — Source Integrity Audit
# Verifică blob-urile Git, SHA-256 și starea working tree.
# Nu modifică fișierele sursă.

set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: Rulează scriptul dintr-un repository Git." >&2
    exit 2
}

cd "$ROOT" || exit 2
mkdir -p audit

python3 - "$ROOT" <<'PY'
import hashlib
import json
import subprocess
import sys

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(sys.argv[1])

PINNED_FILES = {
    "P2/benchmarks/benchmark_config.json":
        "ae16afea13229c95861604475df45e8eebce6b4f",

    "P2/benchmarks/benchmark_contract.py":
        "1561bf6cf3076e871474df15d474db06672df58f",

    "P2/benchmarks/benchmark_runner.py":
        "03a63fec41a099944017d9c95d53c3b8656359a3",

    "P2/tests/test_benchmark.py":
        "0059779c8301b3ca8e25220e940db5a8abbba3d6",
}

VALIDATOR_PATH = "P2/benchmarks/validate_benchmark.py"

VALIDATOR_BASELINE = (
    "eb6f382fb70a1f04750b72931ef54f77eb28c470"
)


def git(*args):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Git command failed"
        )

    return result.stdout.strip()


report = {
    "audit": "source_integrity",
    "timestamp_utc": datetime.now(
        timezone.utc
    ).isoformat(),
    "status": "PASS",
    "files": {},
    "validator_baseline": {},
    "working_tree": {},
    "issues": [],
}


# ---------------------------------------------------------
# 1. Verificarea fișierelor cu blob SHA fixat
# ---------------------------------------------------------

for relative_path, expected_blob in PINNED_FILES.items():

    path = ROOT / relative_path

    item = {
        "exists": path.is_file(),
        "expected_git_blob": expected_blob,
    }

    if not path.is_file():

        item["status"] = "FAIL"

        report["status"] = "FAIL"

        report["issues"].append(
            f"Missing file: {relative_path}"
        )

    else:

        content = path.read_bytes()

        actual_blob = git(
            "hash-object",
            "--",
            relative_path,
        )

        sha256 = hashlib.sha256(
            content
        ).hexdigest()

        matches = actual_blob == expected_blob

        item.update({
            "git_blob": actual_blob,
            "sha256": sha256,
            "matches_baseline_blob": matches,
            "status": "PASS" if matches else "FAIL",
        })

        if not matches:

            report["status"] = "FAIL"

            report["issues"].append(
                f"{relative_path}: "
                f"expected {expected_blob}, "
                f"found {actual_blob}"
            )

    report["files"][relative_path] = item


# ---------------------------------------------------------
# 2. Recuperarea baseline-ului original al validatorului
# ---------------------------------------------------------

try:

    object_type = git(
        "cat-file",
        "-t",
        VALIDATOR_BASELINE,
    )

    original_content = subprocess.run(
        [
            "git",
            "cat-file",
            "blob",
            VALIDATOR_BASELINE,
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout

    actual_blob = hashlib.sha1(
        b"blob "
        + str(len(original_content)).encode("ascii")
        + b"\0"
        + original_content
    ).hexdigest()

    original_sha256 = hashlib.sha256(
        original_content
    ).hexdigest()

    valid = (
        object_type == "blob"
        and actual_blob == VALIDATOR_BASELINE
    )

    report["validator_baseline"] = {
        "path": VALIDATOR_PATH,
        "expected_git_blob": VALIDATOR_BASELINE,
        "object_type": object_type,
        "git_blob": actual_blob,
        "sha256": original_sha256,
        "status": "PASS" if valid else "FAIL",
    }

    if not valid:

        report["status"] = "FAIL"

        report["issues"].append(
            "Original validator baseline verification failed"
        )

except Exception as exc:

    report["validator_baseline"] = {
        "path": VALIDATOR_PATH,
        "expected_git_blob": VALIDATOR_BASELINE,
        "status": "NOT VERIFIED",
        "error": str(exc),
    }

    if report["status"] == "PASS":
        report["status"] = "NOT VERIFIED"


# ---------------------------------------------------------
# 3. Starea repository-ului
# ---------------------------------------------------------

try:

    porcelain = git(
        "status",
        "--porcelain",
    )

    report["working_tree"] = {
        "branch": git(
            "branch",
            "--show-current",
        ),
        "commit": git(
            "rev-parse",
            "HEAD",
        ),
        "clean": not bool(porcelain),
        "status_lines": porcelain.splitlines(),
        "status": "PASS",
    }

except Exception as exc:

    report["working_tree"] = {
        "status": "NOT VERIFIED",
        "error": str(exc),
    }

    if report["status"] == "PASS":
        report["status"] = "NOT VERIFIED"


# ---------------------------------------------------------
# 4. Salvarea raportului
# ---------------------------------------------------------

output = ROOT / "audit" / "source_integrity.json"

output.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

print(
    json.dumps(
        {
            "status": report["status"],
            "report": "audit/source_integrity.json",
        },
        indent=2,
    )
)

sys.exit(
    1 if report["status"] == "FAIL" else 0
)

PY

exit $?
