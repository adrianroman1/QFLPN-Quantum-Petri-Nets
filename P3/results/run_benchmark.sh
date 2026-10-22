#!/usr/bin/env bash

set -Eeuo pipefail

# QFLPN P3 reproducible benchmark and evidence generation.
# The authoritative CSV schema is owned by results/validate_benchmark.py.
# Historical rows are preserved and validated independently from the
# configuration-specific validation of the newly generated record.

N="${N:-1000000}"
WARMUP="${WARMUP:-5}"
ITERATIONS="${ITERATIONS:-10}"
THRESHOLD="${THRESHOLD:-4096}"
PARALLELISM="${PARALLELISM:-2}"
RUN_ID="${RUN_ID:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P3_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$P3_DIR/.." && pwd)"

RAW_ROOT="$P3_DIR/results/raw"
BENCHMARK_DIR="$P3_DIR/benchmarks"
CSV_FILE="$BENCHMARK_DIR/benchmark_results.csv"
VALIDATOR="$P3_DIR/results/validate_benchmark.py"
PYTHON_TEST="$P3_DIR/results/test_validate_benchmark.py"

fail() {
    echo "[FAIL] $*" >&2
    exit 1
}

positive_integer() {
    local name="$1"
    local value="$2"

    [[ "$value" =~ ^[0-9]+$ ]] ||
        fail "$name must be an integer"

    (( value > 0 )) ||
        fail "$name must be positive"
}

nonnegative_integer() {
    local name="$1"
    local value="$2"

    [[ "$value" =~ ^[0-9]+$ ]] ||
        fail "$name must not be negative"
}

positive_integer N "$N"
nonnegative_integer WARMUP "$WARMUP"
positive_integer ITERATIONS "$ITERATIONS"
positive_integer THRESHOLD "$THRESHOLD"
positive_integer PARALLELISM "$PARALLELISM"

for executable in java mvn python3 sha256sum git date; do
    command -v "$executable" >/dev/null 2>&1 ||
        fail "Required executable not found: $executable"
done

[[ -f "$VALIDATOR" ]] ||
    fail "Validator not found: $VALIDATOR"

[[ -f "$PYTHON_TEST" ]] ||
    fail "Python validator tests not found: $PYTHON_TEST"

python3 -m pytest --version >/dev/null 2>&1 ||
    fail "pytest is required: python3 -m pip install pytest"

cd "$ROOT_DIR"

GIT_COMMIT="$(git rev-parse HEAD)"
GIT_BRANCH="$(git branch --show-current)"

if [[ -z "$RUN_ID" ]]; then
    RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${GIT_COMMIT:0:12}-$$"
fi

[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] ||
    fail "RUN_ID contains unsupported characters"

RAW_DIR="$RAW_ROOT/$RUN_ID"
LOG_FILE="$RAW_DIR/benchmark.log"
ENV_FILE="$RAW_DIR/environment.txt"
REPORT_FILE="$RAW_DIR/validation-report.json"
LATEST_CSV="$RAW_DIR/latest_benchmark_result.csv"
CHECKSUM_FILE="$RAW_DIR/SHA256SUMS.txt"

mkdir -p "$RAW_ROOT" "$BENCHMARK_DIR"

[[ ! -e "$RAW_DIR" ]] ||
    fail "Evidence directory already exists: $RAW_DIR"

mkdir "$RAW_DIR"

exec 3>&1 4>&2
: > "$LOG_FILE"
exec > "$LOG_FILE" 2>&1

echo "QFLPN P3 REPRODUCIBLE BENCHMARK"
echo "UTC start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Repository: $ROOT_DIR"
echo "Git branch: $GIT_BRANCH"
echo "Git commit: $GIT_COMMIT"
echo "Run ID: $RUN_ID"

# ------------------------------------------------------------
# Environment evidence.
# ------------------------------------------------------------

{
    echo "QFLPN P3 EXECUTION ENVIRONMENT"
    echo "Run ID: $RUN_ID"
    echo
    echo "UTC timestamp:"
    date -u +%Y-%m-%dT%H:%M:%SZ
    echo
    echo "Git branch:"
    echo "$GIT_BRANCH"
    echo
    echo "Git commit:"
    echo "$GIT_COMMIT"
    echo
    echo "Git status:"
    git status --short
    echo
    echo "Java version:"
    java -version
    echo
    echo "Maven version:"
    mvn --version
    echo
    echo "Python version:"
    python3 --version
    echo
    echo "Pytest version:"
    python3 -m pytest --version
    echo
    echo "Operating system:"
    uname -a
    echo
    echo "CPU:"
    if command -v lscpu >/dev/null 2>&1; then
        lscpu
    else
        echo "lscpu unavailable"
    fi
    echo
    echo "Memory:"
    if command -v free >/dev/null 2>&1; then
        free -h
    else
        echo "free unavailable"
    fi
    echo
    echo "Benchmark configuration:"
    echo "N=$N"
    echo "NNZ=$((2 * N))"
    echo "WARMUP=$WARMUP"
    echo "ITERATIONS=$ITERATIONS"
    echo "THRESHOLD=$THRESHOLD"
    echo "PARALLELISM=$PARALLELISM"
    echo
    echo "Expected workload:"
    echo "A[i,i] = 1.0"
    echo "A[i,i+1] = 0.5"
    echo "A[N-1,0] = 0.5"
    echo "x[i] = 1.0"
    echo "Expected y[i] = 1.5"
    echo "Numerical tolerance = 1.0e-12"
} > "$ENV_FILE" 2>&1

echo "[PASS] Environment captured"

# ------------------------------------------------------------
# P3 Java tests and compilation.
# ------------------------------------------------------------

echo
echo "=== P3 MAVEN CLEAN TEST ==="

mvn -B -f "$P3_DIR/pom.xml" clean test

echo "[PASS] P3 Maven tests"

# ------------------------------------------------------------
# Python validator regression tests.
# ------------------------------------------------------------

echo
echo "=== PYTHON VALIDATOR TESTS ==="

python3 -m pytest "$PYTHON_TEST" -v

echo "[PASS] Python validator tests"

# ------------------------------------------------------------
# Validate existing CSV structure and historical records.
# ------------------------------------------------------------

echo
echo "=== CSV BASELINE VALIDATION ==="

BEFORE_COUNT="$(
python3 - "$CSV_FILE" "$VALIDATOR" <<'PY'
import csv
import importlib.util
import sys
from pathlib import Path

csv_path = Path(sys.argv[1])
validator_path = Path(sys.argv[2])

spec = importlib.util.spec_from_file_location(
    "p3_benchmark_validator",
    validator_path,
)
if spec is None or spec.loader is None:
    raise SystemExit("Cannot load benchmark validator")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

expected_header = module.EXPECTED_HEADER

if not csv_path.exists():
    print(0)
    raise SystemExit(0)

if not csv_path.is_file():
    raise SystemExit("Benchmark CSV path is not a regular file")

if csv_path.stat().st_size == 0:
    raise SystemExit("Existing benchmark CSV is empty")

with csv_path.open("r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)

    if reader.fieldnames != expected_header:
        raise SystemExit(
            "Existing CSV header does not match the "
            "authoritative schema"
        )

    rows = list(reader)

    if not rows:
        raise SystemExit(
            "Existing benchmark CSV contains no data records"
        )

    for index, row in enumerate(rows, start=1):
        if None in row:
            raise SystemExit(
                f"Existing CSV row {index} has extra columns"
            )

        if any(value is None for value in row.values()):
            raise SystemExit(
                f"Existing CSV row {index} has missing fields"
            )

print(len(rows))
PY
)"

echo "Existing CSV records: $BEFORE_COUNT"

if [[ -f "$CSV_FILE" ]]; then
    python3 "$VALIDATOR" --csv "$CSV_FILE"
    echo "[PASS] Existing benchmark records validated"
else
    echo "[INFO] No previous CSV; writer will create the file"
fi

# ------------------------------------------------------------
# Execute Java benchmark.
# ------------------------------------------------------------

echo
echo "=== JAVA BENCHMARK ==="

cd "$P3_DIR"

java \
    -cp target/classes \
    hpc.csr.BenchmarkRunner \
    "--n=$N" \
    "--warmup=$WARMUP" \
    "--iterations=$ITERATIONS" \
    "--threshold=$THRESHOLD" \
    "--parallelism=$PARALLELISM"

echo "[PASS] Java benchmark process"

# ------------------------------------------------------------
# Require exactly one new CSV row.
# ------------------------------------------------------------

echo
echo "=== CSV PROVENANCE CHECK ==="

AFTER_COUNT="$(
python3 - "$CSV_FILE" "$VALIDATOR" <<'PY'
import csv
import importlib.util
import sys
from pathlib import Path

csv_path = Path(sys.argv[1])
validator_path = Path(sys.argv[2])

if not csv_path.is_file():
    raise SystemExit("Benchmark CSV was not created")

spec = importlib.util.spec_from_file_location(
    "p3_benchmark_validator",
    validator_path,
)
if spec is None or spec.loader is None:
    raise SystemExit("Cannot load benchmark validator")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with csv_path.open("r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)

    if reader.fieldnames != module.EXPECTED_HEADER:
        raise SystemExit(
            "Generated CSV header does not match "
            "the authoritative schema"
        )

    rows = list(reader)

    if not rows:
        raise SystemExit("Generated CSV contains no records")

    for index, row in enumerate(rows, start=1):
        if None in row:
            raise SystemExit(
                f"Generated CSV row {index} has extra columns"
            )

        if any(value is None for value in row.values()):
            raise SystemExit(
                f"Generated CSV row {index} has missing fields"
            )

print(len(rows))
PY
)"

EXPECTED_COUNT=$((BEFORE_COUNT + 1))

[[ "$AFTER_COUNT" -eq "$EXPECTED_COUNT" ]] ||
    fail "Expected exactly one new CSV record; expected=$EXPECTED_COUNT actual=$AFTER_COUNT"

echo "[PASS] Exactly one new CSV record"

# ------------------------------------------------------------
# Validate every CSV record without imposing the new run's
# configuration on historical records.
# ------------------------------------------------------------

echo
echo "=== COMPLETE CSV VALIDATION ==="

python3 "$VALIDATOR" --csv "$CSV_FILE"

echo "[PASS] All historical and current CSV records are valid"

# ------------------------------------------------------------
# Extract the newly appended record into an immutable,
# run-specific one-row CSV file.
# ------------------------------------------------------------

echo
echo "=== LATEST RECORD EXTRACTION ==="

python3 - "$CSV_FILE" "$LATEST_CSV" "$VALIDATOR" <<'PY'
import csv
import importlib.util
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
validator_path = Path(sys.argv[3])

spec = importlib.util.spec_from_file_location(
    "p3_benchmark_validator",
    validator_path,
)
if spec is None or spec.loader is None:
    raise SystemExit("Cannot load benchmark validator")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with source_path.open("r", encoding="utf-8", newline="") as source:
    reader = csv.DictReader(source)

    if reader.fieldnames != module.EXPECTED_HEADER:
        raise SystemExit("Source CSV header mismatch")

    rows = list(reader)

if not rows:
    raise SystemExit("Source CSV contains no benchmark records")

latest = rows[-1]

if None in latest or any(value is None for value in latest.values()):
    raise SystemExit("Latest CSV record is structurally invalid")

with output_path.open("w", encoding="utf-8", newline="") as output:
    writer = csv.DictWriter(
        output,
        fieldnames=module.EXPECTED_HEADER,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerow(latest)

print(f"Extracted latest record to: {output_path}")
PY

[[ -s "$LATEST_CSV" ]] ||
    fail "Latest benchmark record CSV is missing or empty"

echo "[PASS] Latest record extracted"

# ------------------------------------------------------------
# Validate the target configuration ONLY against the newly
# generated record. Historical 1/2 records remain preserved.
# ------------------------------------------------------------

echo
echo "=== TARGET CONFIGURATION VALIDATION ==="

python3 "$VALIDATOR" \
    --csv "$LATEST_CSV" \
    --expected-n "$N" \
    --warmup "$WARMUP" \
    --iterations "$ITERATIONS" \
    --threshold "$THRESHOLD" \
    --parallelism "$PARALLELISM" \
    --expected-row-count 1 \
    --report-json "$REPORT_FILE"

echo "[PASS] Latest record matches requested configuration"

# ------------------------------------------------------------
# Evidence presence and non-empty files.
# ------------------------------------------------------------

echo
echo "=== EVIDENCE CHECK ==="

for artifact in \
    "$CSV_FILE" \
    "$LATEST_CSV" \
    "$LOG_FILE" \
    "$ENV_FILE" \
    "$REPORT_FILE"; do

    [[ -s "$artifact" ]] ||
        fail "Missing or empty evidence file: $artifact"
done

echo "[PASS] Complete CSV exists"
echo "[PASS] Latest-record CSV exists"
echo "[PASS] Execution log exists"
echo "[PASS] Environment report exists"
echo "[PASS] Validation JSON exists"

# Stop redirecting before hashing the log.
exec 1>&3 2>&4

cd "$P3_DIR"

sha256sum \
    "benchmarks/benchmark_results.csv" \
    "results/raw/$RUN_ID/latest_benchmark_result.csv" \
    "results/raw/$RUN_ID/benchmark.log" \
    "results/raw/$RUN_ID/environment.txt" \
    "results/raw/$RUN_ID/validation-report.json" \
    > "results/raw/$RUN_ID/SHA256SUMS.txt"

[[ -s "results/raw/$RUN_ID/SHA256SUMS.txt" ]] ||
    fail "Run-specific SHA256SUMS.txt was not generated"

sha256sum -c "results/raw/$RUN_ID/SHA256SUMS.txt"

echo "[PASS] SHA-256 verification"
echo "[PASS] Run ID: $RUN_ID"
echo "[PASS] Evidence directory: P3/results/raw/$RUN_ID"
