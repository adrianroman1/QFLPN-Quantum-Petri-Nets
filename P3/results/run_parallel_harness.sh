#!/usr/bin/env bash
# =============================================================================
# P3 parallel SpMV harness - ONE COMMAND:
#
#     bash P3/results/run_parallel_harness.sh
#
# Everything is produced automatically into
#     P3/results/harness/<RUN_ID>/
# and nothing from earlier runs is ever deleted or overwritten:
#     harness_raw_iterations.csv   every timed multiplication (raw)
#     harness_forks.csv            per fork: bit-exactness, setup, peak heap
#     harness_stream.csv           memory-bandwidth ceiling (triad)
#     harness_preflight.csv        memory/index-capacity preflight decisions
#     harness_skipped.csv          every skipped configuration WITH its reason
#     harness_summary.csv          median, 95% CI, speedup, efficiency, GB/s
#     harness_report.txt / .md     human-readable reports
#     harness_verdict.json         criteria C1..C7 and overall verdict
#     environment.json             hardware, JVM, flags, commit
#     reproduce.sh                 exact command that reproduces this run
#     MANIFEST.txt, SHA256SUMS.txt integrity of every file above
#
# Tunables (environment variables, defaults in brackets):
#   SIZES        [1000000 2000000 7000000 10000000]   up to 30000000
#   WORKLOADS    [UNIFORM_2 POWERLAW]
#   STRATEGIES   [SEQ FJ_PLAN STATIC]
#   PARALLELISMS [1 2 4]    values above the core count are skipped, not run
#   THRESHOLDS   [4096]  recursion thresholds for FJ_PLAN (sweep, e.g. "256 1024 4096 16384")
#   THRESHOLD_MODE [ROW_THRESHOLD]  or NNZ_THRESHOLD
#   FORKS [5] WARMUP [10] ITERATIONS [10]   -> 50 samples per configuration
#   STRICT [0]   1 = exit non-zero unless the overall verdict is PASS
#   P3_SRC_DIR   [P3/code]  Java sources to compile (used by the build-failure test)
#   HARNESS_OUT_DIR [P3/results/harness/<RUN_ID>]  output directory; must not exist
#                   (p3_validation points it into P3/results/raw/<RUN_ID>/)
#   HEAP_MB [3072]   fixed heap (-Xms == -Xmx); GC is fixed to ParallelGC
#   RUN_ID           [h3-<UTC timestamp>-<short commit>]
#
# 100M states are never timed here: N above 30M is refused and recorded in
# harness_skipped.csv; the memory model for 70M and 100M is produced by
# tools/generate_results_md.py as a resource envelope only.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
P3_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${P3_DIR}/.." && pwd)"

SIZES="${SIZES:-1000000 2000000 7000000 10000000}"
WORKLOADS="${WORKLOADS:-UNIFORM_2 POWERLAW}"
STRATEGIES="${STRATEGIES:-SEQ FJ_PLAN STATIC}"
PARALLELISMS="${PARALLELISMS:-1 2 4}"
THRESHOLDS="${THRESHOLDS:-4096}"
THRESHOLD_MODE="${THRESHOLD_MODE:-ROW_THRESHOLD}"
STRICT="${STRICT:-0}"
SRC_DIR="${P3_SRC_DIR:-${P3_DIR}/code}"
FORKS="${FORKS:-5}"
WARMUP="${WARMUP:-10}"
ITERATIONS="${ITERATIONS:-10}"
HEAP_MB="${HEAP_MB:-3072}"
MAX_N=30000000

COMMIT="$(git -C "${REPO_DIR}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ID="${RUN_ID:-h3-${STAMP}-${COMMIT}}"
OUT="${HARNESS_OUT_DIR:-${P3_DIR}/results/harness/${RUN_ID}}"

if [ -e "${OUT}" ]; then
  echo "Refusing to reuse existing run directory: ${OUT}" >&2
  exit 1
fi

mkdir -p "${OUT}"
BUILD="$(mktemp -d)"
trap 'rm -rf "${BUILD}"' EXIT

# Fixed JVM configuration (declared in environment.json and in every fork row).
JVM_FLAGS=(
  "-Xms${HEAP_MB}m" "-Xmx${HEAP_MB}m"
  "-XX:+UseParallelGC" "-XX:+AlwaysPreTouch"
)
HARNESS="hpc.csr.harness.ParallelSpmvHarness"

echo "[1/8] compile (javac) ..."
# Fail-closed build: the real javac exit status is kept, the full log is
# stored as an artifact, and any error stops the run before anything is
# measured. Output is never filtered and never swallowed.
if ! javac -nowarn -d "${BUILD}" \
      "${SRC_DIR}"/*.java \
      "${P3_DIR}/benchmarks/harness/ParallelSpmvHarness.java" \
      > "${OUT}/build.log" 2>&1; then
  echo "BUILD_FAILED" > "${OUT}/BUILD_FAILED.txt"
  echo "BUILD_FAILED: javac returned a non-zero status." >&2
  echo "P3_VALIDATION_FAILED: nothing was measured. Log: ${OUT}/build.log" >&2
  cat "${OUT}/build.log" >&2
  exit 1
fi

run_java() { java "${JVM_FLAGS[@]}" -cp "${BUILD}" "${HARNESS}" "$@"; }

CORES="$(run_java mode=cores)"
echo "      cores visible to the JVM: ${CORES}"

echo "item,reason" > "${OUT}/harness_skipped.csv"
echo "n,workload,nnz,csr_bytes,model_peak_bytes,max_heap_bytes,verdict,reason" \
  > "${OUT}/harness_preflight.csv"
echo "run_id,commit_sha,fork,iteration,workload,n,nnz,strategy,parallelism,elapsed_ms" \
  > "${OUT}/harness_raw_iterations.csv"
echo "run_id,fork,workload,n,nnz,strategy,parallelism,bit_exact,y_hash,setup_ms,peak_heap_after_build_bytes,peak_heap_total_bytes,max_heap_bytes,processors,java_version,jvm_flags" \
  > "${OUT}/harness_forks.csv"
echo "run_id,parallelism,triad_gbs_best,triad_gbs_median,array_doubles" \
  > "${OUT}/harness_stream.csv"

# Parallelism values above the core count would oversubscribe: skip, say why.
P_RUN=()
for p in ${PARALLELISMS}; do
  if [ "${p}" -le "${CORES}" ]; then
    P_RUN+=("${p}")
  else
    echo "p=${p},\"requires ${p} cores but the JVM sees ${CORES}; skipped to avoid oversubscription\"" \
      >> "${OUT}/harness_skipped.csv"
    echo "      skip p=${p}: only ${CORES} core(s)"
  fi
done
P_CSV="$(IFS=,; echo "${P_RUN[*]}")"
STRAT_CSV="$(echo "${STRATEGIES}" | tr ' ' ',')"

echo "[2/8] memory-bandwidth ceiling (triad) ..."
run_java mode=stream run="${RUN_ID}" p="${P_CSV}" reps=15 \
  out="${OUT}/harness_stream.csv"

echo "[3/8] preflight and measurement ..."
for N in ${SIZES}; do
  if [ "${N}" -gt "${MAX_N}" ]; then
    echo "n=${N},\"above the ${MAX_N} timing cap; resource envelope only\"" \
      >> "${OUT}/harness_skipped.csv"
    echo "      skip n=${N}: above timing cap"
    continue
  fi

  for W in ${WORKLOADS}; do
    LINE="$(run_java mode=preflight n="${N}" workload="${W}")"
    echo "${LINE#PREFLIGHT,}" >> "${OUT}/harness_preflight.csv"
    VERDICT="$(echo "${LINE}" | cut -d, -f8)"

    if [ "${VERDICT}" != "RUN" ]; then
      REASON="$(echo "${LINE}" | cut -d, -f9-)"
      echo "n=${N} workload=${W},${REASON}" >> "${OUT}/harness_skipped.csv"
      echo "      skip n=${N} ${W}: preflight refused"
      continue
    fi

    for ((F = 0; F < FORKS; F++)); do
      echo "      n=${N} ${W} fork $((F + 1))/${FORKS}"
      run_java mode=child run="${RUN_ID}" commit="${COMMIT}" fork="${F}" \
        n="${N}" workload="${W}" p="${P_CSV}" strategies="${STRAT_CSV}" \
        warmup="${WARMUP}" iterations="${ITERATIONS}" \
        thresholds="$(echo "${THRESHOLDS}" | tr ' ' ',')" \
        thresholdMode="${THRESHOLD_MODE}" \
        raw="${OUT}/harness_raw_iterations.csv" \
        forks="${OUT}/harness_forks.csv"
    done
  done
done

echo "[4/8] environment ..."
{
  echo "{"
  echo "  \"run_id\": \"${RUN_ID}\","
  echo "  \"commit\": \"${COMMIT}\","
  echo "  \"utc\": \"${STAMP}\","
  echo "  \"cores_visible_to_jvm\": ${CORES},"
  echo "  \"nproc\": \"$(nproc 2>/dev/null || echo unknown)\","
  echo "  \"heap_mb\": ${HEAP_MB},"
  echo "  \"jvm_flags\": \"${JVM_FLAGS[*]}\","
  echo "  \"java\": \"$(java -version 2>&1 | head -1 | tr -d '"')\","
  echo "  \"os\": \"$(uname -srm)\","
  echo "  \"cpu_model\": \"$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ *//' || echo unknown)\","
  echo "  \"mem_total_kb\": \"$(grep -m1 MemTotal /proc/meminfo 2>/dev/null | tr -s ' ' | cut -d' ' -f2 || echo unknown)\","
  echo "  \"sizes\": \"${SIZES}\","
  echo "  \"workloads\": \"${WORKLOADS}\","
  echo "  \"strategies\": \"${STRATEGIES}\","
  echo "  \"parallelisms_requested\": \"${PARALLELISMS}\","
  echo "  \"parallelisms_run\": \"${P_CSV}\","
  echo "  \"thresholds\": \"${THRESHOLDS}\","
  echo "  \"threshold_mode\": \"${THRESHOLD_MODE}\","
  echo "  \"strict\": ${STRICT},"
  echo "  \"forks\": ${FORKS},"
  echo "  \"warmup\": ${WARMUP},"
  echo "  \"iterations\": ${ITERATIONS}"
  echo "}"
} > "${OUT}/environment.json"

cat > "${OUT}/reproduce.sh" <<EOF
#!/usr/bin/env bash
# Reproduces run ${RUN_ID} (commit ${COMMIT}) with the same parameters.
# Note: results depend on the machine; compare environment.json first.
set -euo pipefail
cd "\$(git rev-parse --show-toplevel)"
git checkout ${COMMIT}
SIZES="${SIZES}" WORKLOADS="${WORKLOADS}" STRATEGIES="${STRATEGIES}" \\
PARALLELISMS="${PARALLELISMS}" THRESHOLDS="${THRESHOLDS}" \\
THRESHOLD_MODE=${THRESHOLD_MODE} FORKS=${FORKS} WARMUP=${WARMUP} \\
ITERATIONS=${ITERATIONS} HEAP_MB=${HEAP_MB} STRICT=${STRICT} \\
bash P3/results/run_parallel_harness.sh
EOF
chmod +x "${OUT}/reproduce.sh"

echo "[5/8] statistics, criteria and reports ..."
python3 "${P3_DIR}/tools/summarize_harness.py" "${OUT}"

echo "[6/8] Results.generated.md and article tables ..."
GEN_FLAGS=()
if [ -n "${HARNESS_OUT_DIR:-}" ]; then
  # Inside p3_validation only the run directory may be written: a file
  # created elsewhere would enter the global manifest without being committed.
  GEN_FLAGS+=("--no-latest-copy")
fi
python3 "${P3_DIR}/tools/generate_results_md.py" --harness "${OUT}" ${GEN_FLAGS[@]+"${GEN_FLAGS[@]}"}

echo "[7/8] manifest ..."
{
  echo "P3 parallel SpMV harness manifest"
  echo "run_id: ${RUN_ID}"
  echo "commit: ${COMMIT}"
  echo "generated_utc: ${STAMP}"
  echo
  echo "files:"
  (cd "${OUT}" && for f in $(ls | grep -v -e '^MANIFEST.txt$' -e '^SHA256SUMS.txt$' | sort); do
     printf '  %-34s %10s bytes\n' "${f}" "$(wc -c < "${f}")"
   done)
} > "${OUT}/MANIFEST.txt"

echo "[8/8] checksums ..."
(cd "${OUT}" && sha256sum $(ls | grep -v '^SHA256SUMS.txt$' | sort) > SHA256SUMS.txt \
  && sha256sum -c SHA256SUMS.txt >/dev/null && echo "      SHA256SUMS.txt verified")

echo
echo "Done. Artifacts: ${OUT}"
VERDICT_OVERALL="$(python3 -c "import json;print(json.load(open('${OUT}/harness_verdict.json'))['overall'])")"
echo "Verdict: ${VERDICT_OVERALL}"

if [ "${STRICT}" = "1" ] && [ "${VERDICT_OVERALL}" != "PASS" ]; then
  echo "STRICT=1: overall verdict is ${VERDICT_OVERALL}, not PASS." >&2
  exit 1
fi
