#!/usr/bin/env bash

set -Eeuo pipefail

# ============================================================
# QFLPN P3 — Reproducible Benchmark Execution
#
# Default:
#   N=1000000
#   WARMUP=5
#   ITERATIONS=10
#   THRESHOLD=4096
#   PARALLELISM=2
#
# Usage:
#   bash P3/results/run_benchmark.sh
#
# Optional:
#   N=1000000 WARMUP=5 ITERATIONS=10 \
#   THRESHOLD=4096 PARALLELISM=2 \
#   bash P3/results/run_benchmark.sh
# ============================================================

N="${N:-1000000}"
WARMUP="${WARMUP:-5}"
ITERATIONS="${ITERATIONS:-10}"
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
ARTIFACT_DIR="$P3_DIR/artifacts"

CSV_FILE="$BENCHMARK_DIR/benchmark_results.csv"
LOG_FILE="$RAW_DIR/benchmark-QFLPN-${N}.log"
ENV_FILE="$RAW_DIR/environment.txt"
CHECKSUM_FILE="$ARTIFACT_DIR/SHA256SUMS.txt"

mkdir -p \
  "$RAW_DIR" \
  "$BENCHMARK_DIR" \
  "$ARTIFACT_DIR"

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

require_positive_integer() {
  local name="$1"
  local value="$2"

  [[ "$value" =~ ^[0-9]+$ ]] \
    || fail "$name must be an integer"

  (( value > 0 )) \
    || fail "$name must be greater than zero"
}

require_nonnegative_integer() {
  local name="$1"
  local value="$2"

  [[ "$value" =~ ^[0-9]+$ ]] \
    || fail "$name must be an integer"

  (( value >= 0 )) \
    || fail "$name must not be negative"
}

require_positive_integer "N" "$N"
require_nonnegative_integer "WARMUP" "$WARMUP"
require_positive_integer "ITERATIONS" "$ITERATIONS"
require_positive_integer "THRESHOLD" "$THRESHOLD"
require_positive_integer "PARALLELISM" "$PARALLELISM"

command -v java >/dev/null 2>&1 \
  || fail "Java executable not found"

command -v mvn >/dev/null 2>&1 \
  || fail "Maven executable not found"

command -v python3 >/dev/null 2>&1 \
  || fail "Python 3 executable not found"

command -v sha256sum >/dev/null 2>&1 \
  || fail "sha256sum executable not found"

cd "$ROOT_DIR"

echo "============================================================"
echo "QFLPN P3 BENCHMARK"
echo "============================================================"

echo "Repository: $ROOT_DIR"
echo "P3 directory: $P3_DIR"
echo "N: $N"
echo "Warmup: $WARMUP"
echo "Iterations: $ITERATIONS"
echo "Threshold: $THRESHOLD"
echo "Parallelism: $PARALLELISM"

# ------------------------------------------------------------
# 1. Capture environment before benchmark execution.
# ------------------------------------------------------------

{
  echo "=== UTC TIMESTAMP ==="
  date -u

  echo
  echo "=== GIT COMMIT ==="
  git rev-parse HEAD

  echo
  echo "=== GIT STATUS BEFORE EXECUTION ==="
  git status --short

  echo
  echo "=== JAVA VERSION ==="
  java -version

  echo
  echo "=== JAVA SYSTEM PROPERTIES ==="
  java -XshowSettings:properties -version

  echo
  echo "=== MAVEN VERSION ==="
  mvn --version

  echo
  echo "=== OPERATING SYSTEM ==="
  uname -a

  echo
  echo "=== CPU INFORMATION ==="
  if command -v lscpu >/dev/null 2>&1; then
    lscpu
  else
    echo "lscpu unavailable"
  fi

  echo
  echo "=== MEMORY INFORMATION ==="
  if command -v free >/dev/null 2>&1; then
    free -h
  else
    echo "free unavailable"
  fi

  echo
  echo "=== BENCHMARK CONFIGURATION ==="
  echo "N=$N"
  echo "WARMUP=$WARMUP"
  echo "ITERATIONS=$ITERATIONS"
  echo "THRESHOLD=$THRESHOLD"
  echo "PARALLELISM=$PARALLELISM"

} > "$ENV_FILE" 2>&1

echo "[PASS] Environment captured"

# ------------------------------------------------------------
# 2. Clean Maven build and complete P3 JUnit suite.
# ------------------------------------------------------------

echo
echo "=== MAVEN CLEAN TEST ==="

mvn -B -f "$P3_DIR/pom.xml" clean test

echo "[PASS] Maven clean test"

# ------------------------------------------------------------
# 3. Execute the benchmark from P3 working directory.
#
# BenchmarkResultWriter uses the relative path:
# benchmarks/benchmark_results.csv
# ------------------------------------------------------------

echo
echo "=== BENCHMARK EXECUTION ==="

cd "$P3_DIR"

set -o pipefail

java \
  -cp target/classes \
  hpc.csr.BenchmarkRunner \
  "--n=$N" \
  "--warmup=$WARMUP" \
  "--iterations=$ITERATIONS" \
  "--threshold=$THRESHOLD" \
  "--parallelism=$PARALLELISM" \
  2>&1 | tee "$LOG_FILE"

echo "[PASS] Benchmark process"

# ------------------------------------------------------------
# 4. Validate the latest CSV record independently.
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
# 5. Generate checksums.
# ------------------------------------------------------------

echo
echo "=== SHA-256 CHECKSUMS ==="

cd "$ROOT_DIR"

sha256sum \
  "$CSV_FILE" \
  "$LOG_FILE" \
  "$ENV_FILE" \
  > "$CHECKSUM_FILE"

cat "$CHECKSUM_FILE"

echo
echo "============================================================"
echo "P3 BENCHMARK EXECUTION COMPLETED"
echo "============================================================"

echo "CSV: $CSV_FILE"
echo "LOG: $LOG_FILE"
echo "ENVIRONMENT: $ENV_FILE"
echo "CHECKSUMS: $CHECKSUM_FILE"
