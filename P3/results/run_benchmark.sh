#!/usr/bin/env bash
set -Eeuo pipefail

# QFLPN P3 — reproducible benchmark execution.
#
# The current RUN_ID owns all run-specific evidence:
#   benchmark-report.json
#   benchmark-report.txt
#   benchmark-report.md
#   validation-report.json
#   SHA256SUMS.txt
#
# Markdown is generated from the CSV row and validation JSON
# belonging to this exact RUN_ID.

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

for executable in java mvn python3 git sha256sum; do
    if ! command -v "$executable" >/dev/null 2>&1; then
        echo "ERROR: Missing executable: $executable" >&2
        exit 1
    fi
done

if [[ ! -f "$VALIDATOR" || -L "$VALIDATOR" ]]; then
    echo "ERROR: Benchmark validator is missing or is a symlink." >&2
    exit 1
fi

if [[ ! -f "$SUMMARY_GENERATOR" || -L "$SUMMARY_GENERATOR" ]]; then
    echo "ERROR: Benchmark summary generator is missing or is a symlink." >&2
    exit 1
fi

if [[ ! "$N" =~ ^[1-9][0-9]*$ \
   || ! "$WARMUP" =~ ^[0-9]+$ \
   || ! "$ITERATIONS" =~ ^[1-9][0-9]*$ \
   || ! "$THRESHOLD" =~ ^[1-9][0-9]*$ \
   || ! "$PARALLELISM" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: Invalid benchmark configuration." >&2
    exit 1
fi

if [[ -z "$RUN_ID" ]]; then
    COMMIT_ID="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
    RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${COMMIT_ID}-$$"
fi

if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR: RUN_ID contains unsupported characters." >&2
    exit 2
fi

export RUN_ID

RUN_DIR="$RAW/$RUN_ID"

mkdir -p "$RAW" "$P3_DIR/benchmarks"

if [[ -L "$RAW" || -L "$RUN_DIR" ]]; then
    echo "ERROR: Raw evidence directory must not be a symlink." >&2
    exit 1
fi

if [[ -e "$RUN_DIR" ]]; then
    if [[ ! -d "$RUN_DIR" ]]; then
        echo "ERROR: RUN_ID output path exists and is not a directory." >&2
        exit 1
    fi

    echo "ERROR: RUN_ID directory already exists: $RUN_DIR" >&2
    echo "A run must not overwrite evidence from an earlier execution." >&2
    exit 1
fi

mkdir -p "$RUN_DIR"

if [[ -L "$CSV" ]]; then
    echo "ERROR: Benchmark CSV must not be a symlink." >&2
    exit 1
fi

if [[ -e "$CSV" && ! -f "$CSV" ]]; then
    echo "ERROR: Benchmark CSV is not a regular file." >&2
    exit 1
fi

echo "P3 benchmark configuration"
echo "RUN_ID=$RUN_ID"
echo "N=$N"
echo "WARMUP=$WARMUP"
echo "ITERATIONS=$ITERATIONS"
echo "THRESHOLD=$THRESHOLD"
echo "PARALLELISM=$PARALLELISM"

# Run the complete Maven test suite before measuring performance.
cd "$ROOT_DIR"
mvn -B -f "$P3_DIR/pom.xml" clean test

# Record the CSV row count before this execution.
before=0

if [[ -f "$CSV" ]]; then
    before="$(($(wc -l < "$CSV") - 1))"
    if (( before < 0 )); then
        echo "ERROR: Benchmark CSV has an invalid line count." >&2
        exit 1
    fi
fi

# Execute Java benchmark with the exact RUN_ID exported above.
cd "$P3_DIR"

java \
    -cp target/classes \
    hpc.csr.BenchmarkRunner \
    "--n=$N" \
    "--warmup=$WARMUP" \
    "--iterations=$ITERATIONS" \
    "--threshold=$THRESHOLD" \
    "--parallelism=$PARALLELISM"

if [[ ! -f "$CSV" || -L "$CSV" ]]; then
    echo "ERROR: Benchmark CSV was not produced as a regular file." >&2
    exit 1
fi

after="$(($(wc -l < "$CSV") - 1))"

if [[ "$after" -ne "$((before + 1))" ]]; then
    echo "ERROR: Expected exactly one new V2 CSV record." >&2
    echo "Before: $before; after: $after" >&2
    exit 1
fi

# Produce validation-report.json for this exact RUN_ID.
VALIDATION_REPORT="$RUN_DIR/validation-report.json"

python3 "$VALIDATOR" \
    --csv "$CSV" \
    --expected-n "$N" \
    --warmup "$WARMUP" \
    --iterations "$ITERATIONS" \
    --threshold "$THRESHOLD" \
    --parallelism "$PARALLELISM" \
    --report-json "$VALIDATION_REPORT"

if [[ ! -s "$VALIDATION_REPORT" || -L "$VALIDATION_REPORT" ]]; then
    echo "ERROR: Current-run validation report is missing, empty, or a symlink." >&2
    exit 1
fi

# Produce benchmark-report.md inside this RUN_ID directory.
#
# --overwrite prevents accidental concatenation with an earlier report.
# --strict-output prevents a failure message from being mistaken for
# a valid run-specific Markdown report.
python3 "$SUMMARY_GENERATOR" \
    --csv "$CSV" \
    --report "$VALIDATION_REPORT" \
    --run-id "$RUN_ID" \
    --output "$RUN_DIR/benchmark-report.md" \
    --overwrite \
    --strict-output

# Verify that all three benchmark reports belong to this execution.
python3 - "$RUN_DIR" "$RUN_ID" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
expected_run_id = sys.argv[2]

required = (
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
        raise SystemExit(f"ERROR: Missing run-specific report: {filename}")

    if path.stat().st_size == 0:
        raise SystemExit(f"ERROR: Empty run-specific report: {filename}")

benchmark_json_path = run_dir / "benchmark-report.json"
validation_json_path = run_dir / "validation-report.json"
benchmark_text_path = run_dir / "benchmark-report.txt"
benchmark_markdown_path = run_dir / "benchmark-report.md"

try:
    benchmark_json = json.loads(
        benchmark_json_path.read_text(encoding="utf-8")
    )
    validation_json = json.loads(
        validation_json_path.read_text(encoding="utf-8")
    )
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"ERROR: Invalid run-specific JSON: {exc}")

if benchmark_json.get("run_id") != expected_run_id:
    raise SystemExit(
        "ERROR: benchmark-report.json RUN_ID does not match current execution."
    )

if benchmark_json.get("validation") != "PASS":
    raise SystemExit(
        "ERROR: benchmark-report.json does not declare VALIDATION=PASS."
    )

if validation_json.get("validation") != "PASS":
    raise SystemExit(
        "ERROR: validation-report.json does not declare VALIDATION=PASS."
    )

latest = validation_json.get("latest_record")

if not isinstance(latest, dict):
    raise SystemExit(
        "ERROR: validation-report.json has no latest_record object."
    )

if latest.get("run_id") != expected_run_id:
    raise SystemExit(
        "ERROR: validation-report.json RUN_ID does not match current execution."
    )

text_content = benchmark_text_path.read_text(encoding="utf-8")
markdown_content = benchmark_markdown_path.read_text(encoding="utf-8")

if f"RUN_ID={expected_run_id}" not in text_content:
    raise SystemExit(
        "ERROR: benchmark-report.txt is not associated with current RUN_ID."
    )

if expected_run_id not in markdown_content:
    raise SystemExit(
        "ERROR: benchmark-report.md is not associated with current RUN_ID."
    )

if "Validation: **PASS**" not in markdown_content:
    raise SystemExit(
        "ERROR: benchmark-report.md does not declare successful validation."
    )

print("PASS: all run-specific reports are associated with RUN_ID.")
PY

# Generate run-specific checksums only after all five evidence files exist.
(
    cd "$P3_DIR"

    sha256sum \
        "benchmarks/benchmark_results_v2.csv" \
        "results/raw/$RUN_ID/benchmark-report.json" \
        "results/raw/$RUN_ID/benchmark-report.md" \
        "results/raw/$RUN_ID/benchmark-report.txt" \
        "results/raw/$RUN_ID/validation-report.json" \
        > "results/raw/$RUN_ID/SHA256SUMS.txt"
)

if [[ ! -s "$RUN_DIR/SHA256SUMS.txt" || -L "$RUN_DIR/SHA256SUMS.txt" ]]; then
    echo "ERROR: Run-specific SHA256SUMS.txt was not generated correctly." >&2
    exit 1
fi

# Verify the run-specific checksum file before reporting success.
(
    cd "$P3_DIR"
    sha256sum --check "results/raw/$RUN_ID/SHA256SUMS.txt"
)

SUMMARY_TEXT="$(
    cat <<EOF
## P3 Benchmark V2

- Run ID: \`$RUN_ID\`
- Validation: **PASS**
- Dimension: $N
- Warm-up / iterations: $WARMUP / $ITERATIONS
- CSV: \`P3/benchmarks/benchmark_results_v2.csv\`
- Run-specific reports: \`P3/results/raw/$RUN_ID/\`
- Markdown producer: \`P3/results/generate_benchmark_summary.py\`
- Run-specific checksums: \`P3/results/raw/$RUN_ID/SHA256SUMS.txt\`

EOF
)"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    printf '%s\n' "$SUMMARY_TEXT" >> "$GITHUB_STEP_SUMMARY"
fi

printf '%s\n' "$SUMMARY_TEXT"
echo "P3 benchmark evidence generated successfully: $RUN_ID"
