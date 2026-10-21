#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

EXPECTED_GIT_SHA="eb6f382fb70a1f04750b72931ef54f77eb28c470"

ORIGINAL="audit/validate_benchmark.original.py"
MIGRATED="P2/benchmarks/validate_benchmark.py"
SOURCE_PATH="P2/benchmarks/validate_benchmark.py"
REPORT="audit/sha_report.json"

for file in "$ORIGINAL" "$MIGRATED"; do
    if [[ ! -f "$file" ]]; then
        echo "FAIL: missing file: $file" >&2
        exit 1
    fi
done

HEAD_BLOB="$(git rev-parse "HEAD:${SOURCE_PATH}")"
ORIGINAL_BLOB="$(git hash-object "$ORIGINAL")"

ORIGINAL_SHA256="$(sha256sum "$ORIGINAL" | awk '{print $1}')"
MIGRATED_SHA256="$(sha256sum "$MIGRATED" | awk '{print $1}')"

printf 'Expected Git SHA: %s\n' "$EXPECTED_GIT_SHA"
printf 'HEAD Git blob:    %s\n' "$HEAD_BLOB"
printf 'Original blob:    %s\n' "$ORIGINAL_BLOB"
printf 'Original SHA256:  %s\n' "$ORIGINAL_SHA256"
printf 'Migrated SHA256:  %s\n' "$MIGRATED_SHA256"

if [[ "$HEAD_BLOB" != "$EXPECTED_GIT_SHA" ]]; then
    echo "FAIL: HEAD source blob mismatch."
    exit 1
fi

if [[ "$ORIGINAL_BLOB" != "$EXPECTED_GIT_SHA" ]]; then
    echo "FAIL: original copy mismatch."
    exit 1
fi

python - "$REPORT" \
    "$EXPECTED_GIT_SHA" \
    "$HEAD_BLOB" \
    "$ORIGINAL_BLOB" \
    "$ORIGINAL_SHA256" \
    "$MIGRATED_SHA256" \
    "$ORIGINAL" \
    "$MIGRATED" <<'PY'
import json
import sys
from pathlib import Path

(
    report_path,
    expected,
    head_blob,
    original_blob,
    original_sha256,
    migrated_sha256,
    original_path,
    migrated_path,
) = sys.argv[1:]

report = {
    "expected_original_git_sha": expected,
    "head_source_git_blob": head_blob,
    "original_copy_git_blob": original_blob,
    "original_sha256": original_sha256,
    "migrated_sha256": migrated_sha256,
    "original_file": original_path,
    "migrated_file": migrated_path,
    "git_identity_pass": (
        expected == head_blob == original_blob
    ),
    "sha256_recorded": bool(
        original_sha256 and migrated_sha256
    ),
}

report["passed"] = (
    report["git_identity_pass"]
    and report["sha256_recorded"]
)

Path(report_path).write_text(
    json.dumps(report, indent=2) + "\n",
    encoding="utf-8",
)

print(json.dumps(report, indent=2))

if not report["passed"]:
    raise SystemExit(1)
PY

echo "SHA VERIFICATION: PASS"
