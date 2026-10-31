#!/usr/bin/env bash
set -Eeuo pipefail

# QFLPN P3 — reproducible benchmark V2 execution.
#
# This script is part of the p3_validation evidence chain.
# It does not modify P1.
#
# Canonical timed dimensions:
#   QFLPN-1M
#   QFLPN-10M
#   QFLPN-70M
#   QFLPN-100M
#
# QFLPN-12 is a correctness fixture, not a timed benchmark.
# QFLPN-30M is not part of the canonical catalog.
#
# The Java BenchmarkRunner performs the authoritative heap preflight
# before allocating the benchmark matrix and vectors.

N="${N:-1000000}"
WARMUP="${WARMUP:-5}"
ITERATIONS="${ITERATIONS:-10}"
THRESHOLD="${THRESHOLD:-4096}"
PARALLELISM="${PARALLELISM:-2}"
RUN_ID="${RUN_ID:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P3_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$P3_DIR/.." && pwd)"

CSV="$P3_DIR/benchmarks/benchmark_results_v2.csv"
RAW="$P3_DIR/results/raw"
VALIDATOR="$P3_DIR/results/validate_benchmark.py"
SUMMARY_GENERATOR="$P3_DIR/results/generate_benchmark_summary.py"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

require_regular_file() {
    local path="$1"
    local description="$2"

    [[ ! -L "$path" ]] ||
        fail "$description must not be a symlink."

    [[ -f "$path" ]] ||
        fail "$description is missing or is not a regular file."
}

require_executable() {
    local executable="$1"

    command -v "$executable" >/dev/null 2>&1 ||
        fail "Missing executable: $executable"
}

for executable in java mvn python3 git sha256sum; do
    require_executable "$executable"
done

require_regular_file "$VALIDATOR" "Benchmark validator"
require_regular_file "$SUMMARY_GENERATOR" "Benchmark summary generator"

# ---------------------------------------------------------------------
# 1. Validate configuration before Maven tests or benchmark execution.
# ---------------------------------------------------------------------

[[ "$N" =~ ^[1-9][0-9]*$ ]] ||
    fail "N must be a positive integer."

[[ "$WARMUP" =~ ^[0-9]+$ ]] ||
    fail "WARMUP must be a nonnegative integer."

[[ "$ITERATIONS" =~ ^[1-9][0-9]*$ ]] ||
    fail "ITERATIONS must be a positive integer."

[[ "$THRESHOLD" =~ ^[1-9][0-9]*$ ]] ||
    fail "THRESHOLD must be a positive integer."

[[ "$PARALLELISM" =~ ^[1-9][0-9]*$ ]] ||
    fail "PARALLELISM must be a positive integer."

# Fail-closed shell-level guard.
# BenchmarkScale in Java remains the authoritative catalog.
case "$N" in
    1000000|10000000|70000000|100000000)
        ;;
    12)
        fail "N=12 is a correctness fixture, not a timed benchmark."
        ;;
    30000000)
        fail "N=30000000 is unsupported. QFLPN-30M is not in BenchmarkScale."
        ;;
    *)
        fail "Unsupported timed dimension N=$N. Allowed: 1000000, 10000000, 70000000, 100000000."
        ;;
esac

if [[ -z "$RUN_ID" ]]; then
    COMMIT_ID="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
    RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${COMMIT_ID}-$$"
fi

[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] ||
    fail "RUN_ID contains unsupported characters."

export RUN_ID

# ---------------------------------------------------------------------
# 2. Resolve and validate execution provenance.
# ---------------------------------------------------------------------

SOURCE_COMMIT="${SOURCE_COMMIT:-${P3_SOURCE_COMMIT:-$(git -C "$ROOT_DIR" rev-parse HEAD)}}"
WORKFLOW_RUN_ID="${P3_WORKFLOW_RUN_ID:-${GITHUB_RUN_ID:-local}}"
V3_DIMENSION="${P3_V3_DIMENSION:-4096}"

[[ "$SOURCE_COMMIT" =~ ^[A-Fa-f0-9]{7,64}$ ]] ||
    fail "SOURCE_COMMIT is missing or invalid."

[[ "$WORKFLOW_RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] ||
    fail "Workflow run ID is invalid."

[[ "$V3_DIMENSION" =~ ^[1-9][0-9]*$ ]] ||
    fail "P3_V3_DIMENSION is invalid."

export SOURCE_COMMIT

mkdir -p "$RAW" "$P3_DIR/benchmarks"

[[ ! -L "$RAW" && -d "$RAW" ]] ||
    fail "Raw evidence directory must be a real directory."

RUN_DIR="$RAW/$RUN_ID"
IDENTITY_FILE="$RUN_DIR/execution-identity.txt"

[[ ! -L "$RUN_DIR" ]] ||
    fail "RUN_ID directory must not be a symlink."

EXPECTED_IDENTITY="$(
    printf '%s\n' \
        "P3_RUN_ID=$RUN_ID" \
        "P3_WORKFLOW_RUN_ID=$WORKFLOW_RUN_ID" \
        "P3_SOURCE_COMMIT=$SOURCE_COMMIT" \
        "P3_V2_DIMENSION=$N" \
        "P3_V3_DIMENSION=$V3_DIMENSION"
)"

if [[ -e "$RUN_DIR" ]]; then
    [[ -d "$RUN_DIR" ]] ||
        fail "RUN_ID output path exists and is not a directory."

    require_regular_file "$IDENTITY_FILE" \
        "Existing execution identity"

    ACTUAL_IDENTITY="$(cat "$IDENTITY_FILE")"

    [[ "$ACTUAL_IDENTITY" == "$EXPECTED_IDENTITY" ]] ||
        fail "Existing RUN_ID identity does not match this execution. Refusing to overwrite evidence."

    echo "PASS: existing RUN_ID identity matches this p3_validation execution."
else
    mkdir "$RUN_DIR" ||
        fail "Could not exclusively create RUN_ID directory."

    IDENTITY_TMP="$RUN_DIR/.execution-identity.tmp"

    [[ ! -e "$IDENTITY_TMP" && ! -L "$IDENTITY_TMP" ]] ||
        fail "Temporary identity path already exists."

    printf '%s\n' "$EXPECTED_IDENTITY" > "$IDENTITY_TMP"
    mv "$IDENTITY_TMP" "$IDENTITY_FILE"

    echo "PASS: new RUN_ID directory and execution identity created."
fi

require_regular_file "$IDENTITY_FILE" "Execution identity"

[[ "$(cat "$IDENTITY_FILE")" == "$EXPECTED_IDENTITY" ]] ||
    fail "Execution identity changed during initialization."

# ---------------------------------------------------------------------
# 3. Validate the existing CSV path.
# ---------------------------------------------------------------------

[[ ! -L "$CSV" ]] ||
    fail "Benchmark CSV must not be a symlink."

if [[ -e "$CSV" && ! -f "$CSV" ]]; then
    fail "Benchmark CSV is not a regular file."
fi

echo "P3 benchmark configuration"
echo "RUN_ID=$RUN_ID"
echo "SOURCE_COMMIT=$SOURCE_COMMIT"
echo "WORKFLOW_RUN_ID=$WORKFLOW_RUN_ID"
echo "N=$N"
echo "WARMUP=$WARMUP"
echo "ITERATIONS=$ITERATIONS"
echo "THRESHOLD=$THRESHOLD"
echo "PARALLELISM=$PARALLELISM"

# ---------------------------------------------------------------------
# 4. Execute the complete Maven test suite.
# ---------------------------------------------------------------------

cd "$ROOT_DIR"

mvn -B -f "$P3_DIR/pom.xml" clean test

# ---------------------------------------------------------------------
# 5. Record the CSV row count before this benchmark execution.
# ---------------------------------------------------------------------

before=0

if [[ -f "$CSV" ]]; then
    line_count="$(wc -l < "$CSV")"

    [[ "$line_count" =~ ^[0-9]+$ ]] ||
        fail "Unable to determine CSV line count."

    (( line_count >= 1 )) ||
        fail "Existing benchmark CSV is empty."

    before=$((line_count - 1))
fi

# ---------------------------------------------------------------------
# 6. Run the Java benchmark with the exact RUN_ID.
# ---------------------------------------------------------------------

cd "$P3_DIR"

java \
    -cp target/classes \
    hpc.csr.BenchmarkRunner \
    "--n=$N" \
    "--warmup=$WARMUP" \
    "--iterations=$ITERATIONS" \
    "--threshold=$THRESHOLD" \
    "--parallelism=$PARALLELISM"

require_regular_file "$CSV" "Benchmark CSV"

after_line_count="$(wc -l < "$CSV")"

[[ "$after_line_count" =~ ^[0-9]+$ ]] ||
    fail "Unable to determine CSV line count after benchmark."

after=$((after_line_count - 1))

[[ "$after" -eq "$((before + 1))" ]] ||
    fail "Expected exactly one new V2 CSV record. Before=$before; after=$after."

# ---------------------------------------------------------------------
# 7. Validate the complete CSV against the requested configuration.
# ---------------------------------------------------------------------

VALIDATION_REPORT="$RUN_DIR/validation-report.json"

python3 "$VALIDATOR" \
    --csv "$CSV" \
    --expected-n "$N" \
    --warmup "$WARMUP" \
    --iterations "$ITERATIONS" \
    --threshold "$THRESHOLD" \
    --parallelism "$PARALLELISM" \
    --report-json "$VALIDATION_REPORT"

require_regular_file "$VALIDATION_REPORT" "Validation report"

[[ -s "$VALIDATION_REPORT" ]] ||
    fail "Validation report is empty."

# ---------------------------------------------------------------------
# 8. Verify the exact current-run record in the validation report.
# ---------------------------------------------------------------------

python3 - "$VALIDATION_REPORT" "$RUN_ID" "$N" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
expected_run_id = sys.argv[2]
expected_dimension = int(sys.argv[3])

try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"ERROR: Invalid validation JSON: {exc}")

if report.get("schema") != "qflpn-benchmark-v2":
    raise SystemExit("ERROR: Unexpected validation schema.")

if report.get("validation") != "PASS":
    raise SystemExit("ERROR: Validation did not return PASS.")

if report.get("all_records_valid") is not True:
    raise SystemExit("ERROR: Not all CSV records are valid.")

latest = report.get("latest_record")

if not isinstance(latest, dict):
    raise SystemExit("ERROR: Missing latest_record object.")

if latest.get("run_id") != expected_run_id:
    raise SystemExit("ERROR: Latest CSV record belongs to another RUN_ID.")

if latest.get("dimension") != expected_dimension:
    raise SystemExit("ERROR: Latest CSV record has the wrong dimension.")

print("PASS: validation report identifies the exact current RUN_ID and dimension.")
PY

# ---------------------------------------------------------------------
# 9. Generate the Markdown report from the validated CSV evidence.
# ---------------------------------------------------------------------

python3 "$SUMMARY_GENERATOR" \
    --csv "$CSV" \
    --report "$VALIDATION_REPORT" \
    --run-id "$RUN_ID" \
    --output "$RUN_DIR/benchmark-report.md" \
    --overwrite \
    --strict-output

# ---------------------------------------------------------------------
# 10. Verify all run-specific reports and execution identity.
# ---------------------------------------------------------------------

python3 - "$RUN_DIR" "$RUN_ID" "$N" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
expected_run_id = sys.argv[2]
expected_dimension = int(sys.argv[3])

required = (
    "execution-identity.txt",
    "benchmark-report.json",
    "benchmark-report.txt",
    "benchmark-report.md",
    "validation-report.json",
)

for filename in required:
    path = run_dir / filename

    if path.is_symlink():
        raise SystemExit(f"ERROR: {filename} must not be a symlink.")

    if not path.is_file():
        raise SystemExit(f"ERROR: Missing report: {filename}")

    if path.stat().st_size == 0:
        raise SystemExit(f"ERROR: Empty report: {filename}")

try:
    benchmark_json = json.loads(
        (run_dir / "benchmark-report.json").read_text(encoding="utf-8")
    )
    validation_json = json.loads(
        (run_dir / "validation-report.json").read_text(encoding="utf-8")
    )
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"ERROR: Invalid run-specific JSON: {exc}")

if benchmark_json.get("run_id") != expected_run_id:
    raise SystemExit("ERROR: Benchmark JSON RUN_ID mismatch.")

if benchmark_json.get("dimension") != expected_dimension:
    raise SystemExit("ERROR: Benchmark JSON dimension mismatch.")

if benchmark_json.get("validation") != "PASS":
    raise SystemExit("ERROR: Benchmark JSON does not declare PASS.")

if validation_json.get("validation") != "PASS":
    raise SystemExit("ERROR: Validation JSON does not declare PASS.")

latest = validation_json.get("latest_record")

if not isinstance(latest, dict):
    raise SystemExit("ERROR: Missing latest_record.")

if latest.get("run_id") != expected_run_id:
    raise SystemExit("ERROR: Validation JSON RUN_ID mismatch.")

if latest.get("dimension") != expected_dimension:
    raise SystemExit("ERROR: Validation JSON dimension mismatch.")

text_content = (
    run_dir / "benchmark-report.txt"
).read_text(encoding="utf-8")

markdown_content = (
    run_dir / "benchmark-report.md"
).read_text(encoding="utf-8")

if f"RUN_ID={expected_run_id}" not in text_content:
    raise SystemExit("ERROR: TXT report RUN_ID mismatch.")

if expected_run_id not in markdown_content:
    raise SystemExit("ERROR: Markdown report RUN_ID mismatch.")

if "Validation: **PASS**" not in markdown_content:
    raise SystemExit("ERROR: Markdown report does not declare PASS.")

print("PASS: all run-specific reports match RUN_ID and dimension.")
PY

# ---------------------------------------------------------------------
# 11. Generate and verify run-specific SHA-256 checksums.
# ---------------------------------------------------------------------

(
    cd "$P3_DIR"

    sha256sum \
        "benchmarks/benchmark_results_v2.csv" \
        "results/raw/$RUN_ID/execution-identity.txt" \
        "results/raw/$RUN_ID/benchmark-report.json" \
        "results/raw/$RUN_ID/benchmark-report.md" \
        "results/raw/$RUN_ID/benchmark-report.txt" \
        "results/raw/$RUN_ID/validation-report.json" \
        > "results/raw/$RUN_ID/SHA256SUMS.txt"
)

require_regular_file "$RUN_DIR/SHA256SUMS.txt" \
    "Run-specific SHA256SUMS.txt"

[[ -s "$RUN_DIR/SHA256SUMS.txt" ]] ||
    fail "Run-specific SHA256SUMS.txt is empty."

(
    cd "$P3_DIR"
    sha256sum --check "results/raw/$RUN_ID/SHA256SUMS.txt"
)

# ---------------------------------------------------------------------
# 12. Publish the p3_validation GitHub Actions step summary.
# ---------------------------------------------------------------------

SUMMARY_TEXT="$(
    cat <<EOF
## P3 Benchmark V2

- Run ID: \`$RUN_ID\`
- Validation: **PASS**
- Benchmark dimension: $N
- Warm-up / measured iterations: $WARMUP / $ITERATIONS
- Parallelism: $PARALLELISM
- Threshold: $THRESHOLD
- CSV: \`P3/benchmarks/benchmark_results_v2.csv\`
- Run-specific evidence: \`P3/results/raw/$RUN_ID/\`
- Execution identity: \`P3/results/raw/$RUN_ID/execution-identity.txt\`
- Validation report: \`P3/results/raw/$RUN_ID/validation-report.json\`
- Markdown report: \`P3/results/raw/$RUN_ID/benchmark-report.md\`
- SHA-256: \`P3/results/raw/$RUN_ID/SHA256SUMS.txt\`

EOF
)"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf '%s\n' "$SUMMARY_TEXT" >> "$GITHUB_STEP_SUMMARY"
fi

printf '%s\n' "$SUMMARY_TEXT"

echo "P3 benchmark evidence generated successfully: $RUN_ID"
