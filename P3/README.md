# P3 – QFLPN sparse transition operator: CSR, parallel SpMV, scaling

P3 implements the sparse transition operator of QFLPN in Java (CSR storage,
sequential and parallel sparse matrix–vector product, SpMV) and the evidence
chain that supports every performance statement: raw measurements, statistics,
manifest and checksums.

Terms used throughout:

- **N** – number of states = number of matrix rows (the matrix is N × N).
  N is a state count, **not** a qubit count.
- **NNZ** – number of stored (non-zero) entries.
- **CSR** – compressed sparse row: `values`, `columnIndices`, `rowPointers`.
- **SpMV** – `y = A·x`. Every row is summed in a fixed order, so every
  strategy below produces output that is **bitwise identical** to the
  sequential product.

## Layout

| Path | Content |
|---|---|
| `code/` | Core classes: `SparseMatrixCSR`, `MultiplyTask`, `SpmvPlan`, `QFLPNCoreEngine`, benchmark runners (V2, V3); execution strategies `SpmvStrategy`, `SequentialSpmvStrategy`, `PlannedForkJoinSpmvStrategy`, `StaticChunkSpmvStrategy`, `SpmvStrategies`; distribution plan `DistributedCsrPartition` and in-process `DistributedSpmvSimulation` |
| `tests/` | JUnit 5 and pytest suites (correctness, bitwise equality, lifecycle, no thread creation per call, distributed plan, validators, integrity tools, build-failure behavior) |
| `benchmarks/` | V2 and V3 CSV artifacts written by CI; `harness/` holds the fork-based measurement harness |
| `results/` | `run_parallel_harness.sh` (one command), V2/V3 validators, hand-written `Results.md`, generated `Results.generated.md`, `harness/<RUN_ID>/` run directories |
| `tools/` | Integrity tools (`compute_checksums.py`, `verify_final_package.py`, …), `summarize_harness.py`, `generate_results_md.py`, `check_harness_gate.py` |
| `hpc/` | `config/hpc-664.json` (target, not evidence), `tools/collect_hpc_inventory.py` (inventory and target validation), `slurm/` (untested template) |
| `reports/` | CI reports (validation, evidence consistency, V3 validation) |
| `MANIFEST.txt`, `SHA256SUMS.txt` | Package manifest and checksums (regenerated and verified by the `p3_validation` workflow) |

## One command

```bash
bash P3/results/run_parallel_harness.sh
```

Requirements: a JDK (21 tested), Python 3 (standard library only), `git`.
Nothing from earlier runs is deleted or overwritten; every run writes to a new
directory `P3/results/harness/<RUN_ID>/` and refuses to reuse an existing one.

Automatic outputs of one run:

| File | Meaning |
|---|---|
| `harness_raw_iterations.csv` | One row per timed multiplication (all raw timings) |
| `harness_forks.csv` | Per fork: bitwise-equality flag, output hash, setup time, peak heap, JVM flags |
| `harness_stream.csv` | Memory-bandwidth ceiling (triad, GB/s) per parallelism |
| `harness_preflight.csv` | Memory and index-capacity decision per N and workload |
| `harness_skipped.csv` | Every skipped configuration with its reason (never silent) |
| `harness_summary.csv` | Median, 95% bootstrap CI, speedup (paired), efficiency, overhead %, GB/s |
| `harness_report.txt`, `harness_report.md` | Human-readable reports |
| `harness_verdict.json` | Criteria C1–C7 and the overall verdict |
| `Results.generated.md`, `article_tables.md`, `article_tables.tex` | Generated from the CSVs, one `run_id` per row |
| `environment.json`, `reproduce.sh` | Machine, JVM and exact reproduction command |
| `MANIFEST.txt`, `SHA256SUMS.txt` | Integrity of every file above (verified at the end of the run) |

### Protocol

- Several forks (default 5), each a separate JVM, with 10 warm-up and 10 timed
  iterations per strategy: 50 samples per configuration (criterion: ≥ 30).
- Strategies are interleaved in rotating order inside every iteration to cancel
  drift. Setup time (matrix construction) is measured separately from kernel
  time.
- Parallelism values above the core count seen by the JVM are **skipped and
  recorded**, not run (no oversubscription).
- Fixed JVM configuration: `-Xms == -Xmx` (default 3072 MB), `-XX:+UseParallelGC`,
  `-XX:+AlwaysPreTouch`. Declared in `environment.json` and in every fork row.
- Statistics use only the standard library: median, bootstrap CI of the median
  (2000 resamples, fixed seed), paired speedup CI.

### Tunables

`SIZES` (default `1000000 2000000 7000000 10000000`, up to `30000000`),
`WORKLOADS` (`UNIFORM_2 POWERLAW`), `STRATEGIES` (`SEQ FJ_PLAN STATIC`),
`PARALLELISMS` (`1 2 4`; wider lists such as `1 2 4 8 16 32 64` are accepted,
values above the visible core count are skipped and recorded),
`THRESHOLDS` (default `4096`; a sweep such as `256 512 1024 2048 4096 8192 16384`
is reported per threshold as `FJ_PLAN_T<threshold>`), `THRESHOLD_MODE`
(`ROW_THRESHOLD` default, or `NNZ_THRESHOLD`), `FORKS`, `WARMUP`, `ITERATIONS`,
`HEAP_MB`, `RUN_ID`, `STRICT` (1 = exit non-zero unless the verdict is PASS),
`HARNESS_OUT_DIR`.

Cost of a sweep: measurements = sizes × workloads × forks × iterations ×
(1 + parallelisms × (thresholds + 1)). Run a threshold sweep on a dedicated
machine, not on every commit.

Example: `SIZES="10000000 30000000" THRESHOLDS="1024 4096 16384" HEAP_MB=8192 bash P3/results/run_parallel_harness.sh`

### Failure behavior (fail-closed)

- A Java compile error stops the run before anything is measured:
  `BUILD_FAILED.txt`, the full `build.log`, and exit status 1.
- `summarize_harness.py` exits with status 2 when the input is absent, has
  missing columns, non-numeric or non-positive timings, or duplicates; an empty
  data set is never a PASS.
- Every configuration declared in `environment.json` (and not skipped with a
  reason) must have observations, otherwise C8 fails; without `environment.json`
  completeness cannot be proven and the verdict is at best PARTIAL.

## Evidence levels

| Level | Meaning |
|---|---|
| **Measured** | At least 30 samples per configuration in a harness run with artifacts |
| **Scalable** | Planned size (30M) without a measured artifact yet |
| **Resource Envelope** | Memory model only, **never timed** (70M, 100M) |

Declared sizes: 1M, 2M, 7M, 10M (measured when a harness run exists), 30M
(scalable), 70M and 100M (envelope). The harness refuses to time N above 30M.

At N = 100,000,000 `UNIFORM_2` needs 200 million entries: CSR payload ≈ 2.8 GB
and a modelled construction peak of ≈ 8 GB; `UNIFORM_100` would need 10 billion
entries, which exceeds the limit of a single Java array and is reported as
infeasible, not as PASS.

## Reading the verdict

`harness_verdict.json` evaluates:

| ID | Criterion |
|---|---|
| C0 | Input present and valid (no empty data, no invalid or duplicated rows) |
| C1 | ≥ 30 samples per configuration (an empty data set fails) |
| C2 | Every strategy bitwise identical to sequential, in every fork |
| C3 | Overhead of each strategy at p = 1 is ≤ 5% of sequential (N ≥ 1M) |
| C4 | Speedup > 1 at p = 2 for N ≥ 10M (lower bound of the 95% CI) |
| C5 | No configuration with N ≥ 1M and p ≥ 2 significantly slower than sequential |
| C6 | Bandwidth ceiling recorded |
| C7 | Skips and preflight refusals documented |
| C8 | Every declared configuration has observations |

A criterion that the machine cannot evaluate (for example C4 on a single-core
machine) is `NOT_EVALUATED` and the overall verdict is `PARTIAL`, never `PASS`.

Bandwidth efficiency above 1.0 means the working set fits (partly) in cache, so
the DRAM ceiling does not apply to that row; read it only at sizes well above
the last-level cache.

## Integration in `p3_validation`

The workflow runs a small harness smoke (1M rows, 2 forks, 15 iterations) into
`P3/results/raw/<RUN_ID>/harness-smoke/`, so the existing upload, evidence index,
global `MANIFEST.txt` / `SHA256SUMS.txt` and the evidence commit pick it up
unchanged. `tools/check_harness_gate.py` blocks the job when the build failed,
when C0, C1, C2, C7 or C8 is not PASS, or when the run's own `SHA256SUMS.txt`
does not match. Performance criteria C3–C6 are reported as warnings only:
shared runners are too noisy for performance gating. The step is intentionally
not part of `ci-outcomes.json` (its stage schema is unchanged); a failure still
stops the job before any later step and therefore prevents `P3_ACCEPTED`.

## Distributed SpMV: plan and simulation (no MPI)

`DistributedCsrPartition` distributes a square CSR matrix by NNZ-balanced row
ranges, remaps each rank's columns to a compact local numbering, and computes
the exact halo plan (which entries of `x` each rank must receive).
`DistributedSpmvSimulation` runs the data flow in one JVM and proves that the
distributed product is bitwise identical to the sequential one for any rank
count.

This is **not MPI**: there is no network and no communication timing, and its
timings must never be reported as cluster results. An MPI program would reuse
`neededColumns(rank)` for the `Alltoallv` counts and `localMultiply` for the
local product. The MPI binding itself is not implemented here.

## HPC target

`hpc/config/hpc-664.json` describes the reference target (16 compute nodes,
664 physical cores, 4 TiB). It is a proposal, not evidence.
`hpc/tools/collect_hpc_inventory.py collect` records what each node and job
really expose (physical cores, affinity mask, cgroup quota, memory, NUMA,
Slurm variables, JDK, MPI); `... validate hpc-664.json node*.json` merges the
inventories and returns PASS only when distinct nodes meet every target
quantity, DEFERRED when inventories are insufficient or absent, FAIL when they
contradict the target. A single JVM with parallelism 664 on one node is
classified as intra-node, not distributed. 672 is an experimental point above
the physical core count and must be reported as oversubscribed.

## Known limits

- The V3 benchmark matrix in CI runs at dimension 4096. At that size the
  sequential kernel takes microseconds, so the V3 speedup column measures task
  dispatch overhead; it is a correctness and sensitivity check, not a scaling
  result. Use the harness for performance statements.
- `StaticChunkSpmvStrategy` keeps a private copy of the CSR arrays (public
  getters only), i.e. one extra CSR payload while it is open.
- GitHub-hosted runners have 4 shared vCPUs and are noisy. Final performance
  numbers should come from a dedicated multi-core machine; CI remains the
  correctness and smoke gate.
- First-touch / NUMA placement cannot be controlled from Java code (the JVM
  zeroes new arrays in the allocating thread); no claim is made about it.
- Speedup of a memory-bound kernel is bounded by memory bandwidth; this is why
  efficiency is reported against a measured bandwidth ceiling.

## Tests

```bash
mvn -f P3/pom.xml test           # Java (JUnit 5)
python -m pytest P3/tests P3/results   # Python tools and validators
```

## Integrity

`MANIFEST.txt` and `SHA256SUMS.txt` are regenerated and verified by the
`p3_validation` workflow in the same run as the tests and benchmarks.
`tools/verify_final_package.py` rejects missing, modified, duplicated or
unexpected files.
