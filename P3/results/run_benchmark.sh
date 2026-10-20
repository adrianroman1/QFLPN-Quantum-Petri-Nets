#!/usr/bin/env bash

set -Eeuo pipefail

# ============================================================
# QFLPN P3 — REPRODUCIBLE BENCHMARK EXECUTION
#
# Outputs:
#   P3/benchmarks/benchmark_results.csv
#   P3/results/raw/benchmark-QFLPN-1000000.log
#   P3/results/raw/environment.txt
#   P3/SHA256SUMS.txt
#
# Manuscript configuration:
#   N=1000000
#   WARMUP=1
#   ITERATIONS=2
#   THRESHOLD=4096
#   PARALLELISM=2
#
# Usage from repository root:
#   bash P3/results/run_benchmark.sh
#
# Optional configuration:
#   N=1000000 WARMUP=1 ITERATIONS=2 \
#   THRESHOLD=4096 PARALLELISM=2 \
#   bash P3/results/run_benchmark.sh
# ============================================================

N="${N:-1000000}"
WARMUP="${WARMUP:-1}"
ITERATIONS="${ITERATIONS:-2}"
THRESHOLD="${THRESHOLD:-4096}"
PARALLELISM="${PARALLELISM:-2}"

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

RAW_DIR="$P3_DIR/results/raw"
BENCHMARK_DIR="$P3_DIR/benchmarks"

CSV_FILE="$BENCHMARK_DIR/benchmark_results.csv"
LOG_FILE="$RAW_DIR/benchmark-QFLPN-${N}.log"
ENV_FILE="$RAW_DIR/environment.txt"
CHECKSUM_FILE="$P3_DIR/SHA256SUMS.txt"

mkdir -p "$RAW_DIR" "$BENCHMARK_DIR"

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

require_positive_integer() {
  local name="$1"
  local value="$2"

  [[ "$value" =~ ^[0-9]+$ ]] ||
    fail "$name must be an integer"

  (( value > 0 )) ||
    fail "$name must be greater than zero"
}

require_nonnegative_integer() {
  local name="$1"
  local value="$2"

  [[ "$value" =~ ^[0-9]+$ ]] ||
    fail "$name must be an integer"

  (( value >= 0 )) ||
    fail "$name must not be negative"
}

require_positive_integer "N" "$N"
require_nonnegative_integer "WARMUP" "$WARMUP"
require_positive_integer "ITERATIONS" "$ITERATIONS"
require_positive_integer "THRESHOLD" "$THRESHOLD"
require_positive_integer "PARALLELISM" "$PARALLELISM"

for command_name in java mvn python3 sha256sum git; do
  command -v "$command_name" >/dev/null 2>&1 ||
    fail "Required command not found: $command_name"
done

cd "$ROOT_DIR"

# Start a complete execution log.
: > "$LOG_FILE"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "QFLPN P3 — BENCHMARK EXECUTION"
echo "============================================================"
echo "UTC start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Repository: $ROOT_DIR"
echo "P3 directory: $P3_DIR"

# ------------------------------------------------------------
# 1. Capture exact source revision and environment.
# ------------------------------------------------------------

GIT_COMMIT="$(git rev-parse HEAD)"
GIT_BRANCH="$(git branch --show-current)"

{
  echo "QFLPN P3 — EXECUTION ENVIRONMENT"
  echo "================================"
  echo
  echo "UTC timestamp:"
  date -u +%Y-%m-%dT%H:%M:%SZ

  echo
  echo "Repository:"
  echo "$ROOT_DIR"

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
  echo "Git tracked modifications:"
  git diff --stat

  echo
  echo "Git staged modifications:"
  git diff --cached --stat

  echo
  echo "Java version:"
  java -version

  echo
  echo "Java properties:"
  java -XshowSettings:properties -version

  echo
  echo "Maven version:"
  mvn --version

  echo
  echo "Operating system:"
  uname -a

  echo
  echo "CPU information:"
  if command -v lscpu >/dev/null 2>&1; then
    lscpu
  else
    echo "lscpu unavailable"
  fi

  echo
  echo "Memory information:"
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
  echo "Benchmark definition:"
  echo "A[i,i] = 1.0"
  echo "A[i,i+1] = 0.5"
  echo "A[N-1,0] = 0.5"
  echo "x[i] = 1.0"
  echo "Expected y[i] = 1.5"
  echo "Numerical tolerance = 1.0e-12"

  echo
  echo "Timing method:"
  echo "System.nanoTime()"

} > "$ENV_FILE" 2>&1

echo "[PASS] Environment captured"
echo "[INFO] Commit: $GIT_COMMIT"

# ------------------------------------------------------------
# 2. Validate the Maven project and execute all Java tests.
# ------------------------------------------------------------

echo
echo "=== MAVEN CLEAN TEST ==="

mvn -B -f "$P3_DIR/pom.xml" clean test

echo "[PASS] Maven clean test"

# ------------------------------------------------------------
# 3. Execute the benchmark.
# ------------------------------------------------------------

echo
echo "=== BENCHMARK EXECUTION ==="

cd "$P3_DIR"

java \
  -cp target/classes \
  hpc.csr.BenchmarkRunner \
  "--n=$N" \
  "--warmup=$WARMUP" \
  "--iterations=$ITERATIONS" \
  "--threshold=$THRESHOLD" \
  "--parallelism=$PARALLELISM"

echo "[PASS] Benchmark process"

# ------------------------------------------------------------
# 4. Validate the persisted CSV independently.
# ------------------------------------------------------------

echo
echo "=== INDEPENDENT CSV VALIDATION ==="

python3 \
  "$P3_DIR/results/validate_benchmark.py" \
  --csv "$CSV_FILE" \
  --expected-n "$N" \
  --warmup "$WARMUP" \
  --iterations "$ITERATIONS" \
  --threshold "$THRESHOLD" \
  --parallelism "$PARALLELISM"

echo "[PASS] Independent CSV validation"

# ------------------------------------------------------------
# 5. Verify that all expected artifacts contain data.
# ------------------------------------------------------------

echo
echo "=== ARTIFACT PRESENCE CHECK ==="

for artifact in "$CSV_FILE" "$LOG_FILE" "$ENV_FILE"; do
  [[ -s "$artifact" ]] ||
    fail "Missing or empty artifact: $artifact"

  echo "[PASS] $artifact"
done

# ------------------------------------------------------------
# 6. Generate root-level SHA-256 manifest.
# ------------------------------------------------------------

echo
echo "=== SHA-256 GENERATION ==="

(
  cd "$P3_DIR"

  sha256sum \
    "benchmarks/benchmark_results.csv" \
    "results/raw/benchmark-QFLPN-${N}.log" \
    "results/raw/environment.txt"
) > "$CHECKSUM_FILE"

[[ -s "$CHECKSUM_FILE" ]] ||
  fail "SHA256SUMS.txt was not generated"

echo "[PASS] SHA-256 manifest generated"

# ------------------------------------------------------------
# 7. Verify checksums immediately.
# ------------------------------------------------------------

echo
echo "=== SHA-256 VERIFICATION ==="

(
  cd "$P3_DIR"
  sha256sum -c SHA256SUMS.txt
)

echo "[PASS] SHA-256 verification"

# ------------------------------------------------------------
# 8. Final execution summary.
# ------------------------------------------------------------

echo
echo "============================================================"
echo "P3 BENCHMARK EXECUTION COMPLETED"
echo "============================================================"

echo "UTC end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Git commit: $GIT_COMMIT"
echo "CSV: $CSV_FILE"
echo "LOG: $LOG_FILE"
echo "ENVIRONMENT: $ENV_FILE"
echo "CHECKSUMS: $CHECKSUM_FILE"

echo
echo "[PASS] Execution pipeline completed"
