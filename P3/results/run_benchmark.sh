#!/usr/bin/env bash
set -Eeuo pipefail

# P3 Lot C: execute the V2 benchmark and validate the new schema.
N="${N:-1000000}"; WARMUP="${WARMUP:-5}"; ITERATIONS="${ITERATIONS:-10}"
THRESHOLD="${THRESHOLD:-4096}"; PARALLELISM="${PARALLELISM:-2}"; RUN_ID="${RUN_ID:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P3_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"; ROOT_DIR="$(cd "$P3_DIR/.." && pwd)"
CSV="$P3_DIR/benchmarks/benchmark_results_v2.csv"; RAW="$P3_DIR/results/raw"
VALIDATOR="$P3_DIR/results/validate_benchmark.py"
for x in java mvn python3; do command -v "$x" >/dev/null || { echo "Missing executable: $x" >&2; exit 1; }; done
[[ "$N" =~ ^[1-9][0-9]*$ && "$WARMUP" =~ ^[0-9]+$ && "$ITERATIONS" =~ ^[1-9][0-9]*$ && "$THRESHOLD" =~ ^[1-9][0-9]*$ && "$PARALLELISM" =~ ^[1-9][0-9]*$ ]] || { echo "Invalid benchmark configuration" >&2; exit 2; }
cd "$ROOT_DIR"
[[ -n "$RUN_ID" ]] || RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short HEAD)-$$"
[[ "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid RUN_ID" >&2; exit 2; }
mkdir -p "$RAW" "$P3_DIR/benchmarks"
export RUN_ID
mvn -B -f "$P3_DIR/pom.xml" clean test
before=0; [[ -f "$CSV" ]] && before="$(($(wc -l < "$CSV")-1))"
cd "$P3_DIR"
java -cp target/classes hpc.csr.BenchmarkRunner "--n=$N" "--warmup=$WARMUP" "--iterations=$ITERATIONS" "--threshold=$THRESHOLD" "--parallelism=$PARALLELISM"
after="$(($(wc -l < "$CSV")-1))"
[[ "$after" -eq "$((before+1))" ]] || { echo "Expected exactly one V2 CSV record" >&2; exit 1; }
REPORT="$RAW/$RUN_ID/validation-report.json"
python3 "$VALIDATOR" --csv "$CSV" --expected-n "$N" --warmup "$WARMUP" --iterations "$ITERATIONS" --threshold "$THRESHOLD" --parallelism "$PARALLELISM" --report-json "$REPORT"
[[ -s "$RAW/$RUN_ID/benchmark-report.txt" && -s "$RAW/$RUN_ID/benchmark-report.md" && -s "$RAW/$RUN_ID/benchmark-report.json" ]] || { echo "Missing run reports" >&2; exit 1; }
{
 echo "## P3 Benchmark V2"
 echo "- Run ID: $RUN_ID"
 echo "- Validation: PASS"
 echo "- Dimension: $N"
 echo "- Warm-up / iterations: $WARMUP / $ITERATIONS"
 echo "- CSV: P3/benchmarks/benchmark_results_v2.csv"
 echo "- Reports: P3/results/raw/$RUN_ID/"
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
(cd "$P3_DIR" && sha256sum "benchmarks/benchmark_results_v2.csv" "results/raw/$RUN_ID/benchmark-report.json" "results/raw/$RUN_ID/benchmark-report.md" "results/raw/$RUN_ID/benchmark-report.txt" "results/raw/$RUN_ID/validation-report.json" > "results/raw/$RUN_ID/SHA256SUMS.txt" && sha256sum -c "results/raw/$RUN_ID/SHA256SUMS.txt")
echo "P3 Lot C benchmark evidence generated: $RUN_ID"
