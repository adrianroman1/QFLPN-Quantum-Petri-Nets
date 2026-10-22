#!/usr/bin/env bash

set -Eeuo pipefail

# QFLPN P3 reproducible benchmark and evidence generation.
#
# Each execution receives a unique evidence directory:
# P3/results/raw/<RUN_ID>/
#
# The benchmark CSV is append-only. Existing measurements are
# never rewritten by this script.

N="${N:-1000000}"
WARMUP="${WARMUP:-5}"
ITERATIONS="${ITERATIONS:-10}"
THRESHOLD="${THRESHOLD:-4096}"
PARALLELISM="${PARALLELISM:-2}"
RUN_ID="${RUN_ID:-}"

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

P3_DIR="$(
    cd "$SCRIPT_DIR/.."
    pwd
)"

ROOT_DIR="$(
    cd "$P3_DIR/.."
    pwd
)"

RAW_ROOT="$P3_DIR/results/raw"
BENCHMARK_DIR="$P3_DIR/benchmarks"

CSV_FILE="$BENCHMARK_DIR/benchmark_results.csv"

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
        fail "$name must be an integer"

    (( value >= 0 )) ||
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

python3 -m pytest --version >/dev/null 2>&1 ||
    fail "pytest is required: python3 -m pip install pytest"

cd "$ROOT_DIR"

GIT_COMMIT="$(git rev-parse HEAD)"
GIT_BRANCH="$(git branch --show-current)"

if [[ -z "$RUN_ID" ]]; then
    RUN_ID="$(
        date -u +%Y%m%dT%H%M%SZ
    )-${GIT_COMMIT:0:12}-$$"
fi

[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] ||
    fail "RUN_ID contains unsupported characters"

RAW_DIR="$RAW_ROOT/$RUN_ID"
LOG_FILE="$RAW_DIR/benchmark.log"
ENV_FILE="$RAW_DIR/environment.txt"
REPORT_FILE="$RAW_DIR/validation-report.json"
CHECKSUM_FILE="$RAW_DIR/SHA256SUMS.txt"

mkdir -p "$RAW_ROOT" "$BENCHMARK_DIR"

if [[ -e "$RAW_DIR" ]]; then
    fail "Evidence directory already exists: $RAW_DIR"
fi

mkdir "$RAW_DIR"

# Preserve the original terminal/CI output streams.
exec 3>&1 4>&2

: > "$LOG_FILE"

# All benchmark output is captured in the unique execution log.
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
# Java test suite.
# ------------------------------------------------------------

echo
echo "=== MAVEN CLEAN TEST ==="

mvn -B -f "$P3_DIR/pom.xml" clean test

echo "[PASS] Maven tests"

# ------------------------------------------------------------
# Python validator regression tests.
# ------------------------------------------------------------

echo
echo "=== PYTHON VALIDATOR TESTS ==="

python3 -m pytest \
    "$P3_DIR/results/test_validate_benchmark.py" \
    -v

echo "[PASS] Python validator tests"

# ------------------------------------------------------------
# Validate the existing CSV before appending a new record.
# ------------------------------------------------------------

echo
echo "=== CSV BASELINE ==="

BEFORE_COUNT="$(
    python3 - "$CSV_FILE" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])

expected = [
    "timestamp",
    "benchmark_id",
    "dimension",
    "non_zero_count",
    "parallelism",
    "threshold",
    "warmup_iterations",
    "measured_iterations",
    "sequential_ms",
    "parallel_ms",
    "speedup",
    "sequential_throughput_states_per_s",
    "parallel_throughput_states_per_s",
    "sequential_expected_error",
    "parallel_expected_error",
    "max_absolute_error",
    "setup_time_ms",
    "cpu",
    "available_memory_bytes",
    "java_version",
    "operating_system",
    "notes",
]

if not path.exists():
    print(0)
    raise SystemExit(0)

if path.stat().st_size == 0:
    raise SystemExit("Existing benchmark CSV is empty")

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as handle:
    reader = csv.DictReader(handle)

    if reader.fieldnames != expected:
        raise SystemExit("Invalid existing CSV header")

    rows = list(reader)

    for index, row in enumerate(rows, start=1):
        if None in row:
            raise SystemExit(
                f"Malformed existing CSV row {index}"
            )

        if any(value is None for value in row.values()):
            raise SystemExit(
                f"Missing field in existing CSV row {index}"
            )

print(len(rows))
PY
)"

echo "Existing CSV records: $BEFORE_COUNT"

# ------------------------------------------------------------
# Execute the Java benchmark.
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
# Require exactly one new CSV record.
# ------------------------------------------------------------

echo
echo "=== CSV PROVENANCE CHECK ==="

AFTER_COUNT="$(
    python3 - "$CSV_FILE" <<'PY'
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])

if not path.is_file():
    raise SystemExit("Benchmark CSV was not created")

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as handle:
    reader = csv.DictReader(handle)

    if reader.fieldnames is None:
        raise SystemExit("Benchmark CSV has no header")

    rows = list(reader)

    for index, row in enumerate(rows, start=1):
        if None in row:
            raise SystemExit(
                f"Malformed benchmark CSV row {index}"
            )

        if any(value is None for value in row.values()):
            raise SystemExit(
                f"Missing field in benchmark CSV row {index}"
            )

print(len(rows))
PY
)"

EXPECTED_COUNT=$((BEFORE_COUNT + 1))

[[ "$AFTER_COUNT" -eq "$EXPECTED_COUNT" ]] ||
    fail "Expected one new CSV record; expected=$EXPECTED_COUNT actual=$AFTER_COUNT"

echo "[PASS] Exactly one new CSV record"

# ------------------------------------------------------------
# Independent validation of the newly appended result.
# ------------------------------------------------------------

echo
echo "=== INDEPENDENT VALIDATION ==="

python3 \
    "$P3_DIR/results/validate_benchmark.py" \
    --csv "$CSV_FILE" \
    --expected-n "$N" \
    --warmup "$WARMUP" \
    --iterations "$ITERATIONS" \
    --threshold "$THRESHOLD" \
    --parallelism "$PARALLELISM" \
    --expected-row-count "$EXPECTED_COUNT" \
    --report-json "$REPORT_FILE"

echo "[PASS] Independent validation"

# ------------------------------------------------------------
# Evidence presence.
# ------------------------------------------------------------

echo
echo "=== EVIDENCE CHECK ==="

for artifact in \
    "$CSV_FILE" \
    "$LOG_FILE" \
    "$ENV_FILE" \
    "$REPORT_FILE"; do

    [[ -s "$artifact" ]] ||
        fail "Missing or empty evidence file: $artifact"
done

echo "[PASS] CSV exists"
echo "[PASS] Execution log exists"
echo "[PASS] Environment report exists"
echo "[PASS] Validation JSON exists"
echo "[PASS] Benchmark execution completed"

# ------------------------------------------------------------
# Close the log before calculating its checksum.
# No benchmark output is written to LOG_FILE after this point.
# ------------------------------------------------------------

exec 1>&3 2>&4

cd "$P3_DIR"

sha256sum \
    "benchmarks/benchmark_results.csv" \
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
