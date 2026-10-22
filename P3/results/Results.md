# P3 — Benchmark Results

## 1. Scope

This document records the correctness and performance evidence
for the P3 Compressed Sparse Row (CSR) sparse matrix-vector
multiplication implementation.

The benchmark measures:

- sequential CSR SpMV;
- parallel CSR SpMV using Java Fork/Join;
- sequential and parallel execution times;
- speedup;
- execution-time reduction;
- numerical consistency;
- execution configuration and environment.

Correctness tests, CI execution and performance measurements
are separate forms of evidence. A passing test suite is not
a performance measurement.

## 2. Correctness fixture and performance workload

### 2.1 Manuscript correctness matrix

The independent correctness test uses the 4 x 4 matrix
defined in Section 13, equation (14), of the P3 manuscript.

CSR representation:

| Property | Value |
|---|---|
| Rows | 4 |
| Columns | 4 |
| NNZ | 7 |
| Values | (4, 2, 3, 1, 5, 2, 6) |
| Column indices | (0, 3, 1, 0, 2, 2, 3) |
| Row pointers | (0, 2, 3, 5, 7) |

For the explicit test input:

x = (1, 2, 3, 4)^T

the expected result is:

y = A*x = (12, 6, 16, 30)^T

The input vector is an explicit test fixture. It is not
represented as a vector explicitly specified by the manuscript.

Test:
`P3/tests/CSRvsDenseOracleTest.java`

### 2.2 Large-scale synthetic benchmark

`BenchmarkRunner.createBenchmarkMatrix(int n)` constructs
a deterministic synthetic sparse matrix.

For each row i:

- A[i,i] = 1.0
- A[i,i+1] = 0.5, when i < N-1
- A[N-1,0] = 0.5, for the final row

For N > 1:

- N rows;
- N columns;
- NNZ = 2N;
- two stored elements per row.

The input vector is:

x[i] = 1.0

The expected output is:

y[i] = 1.5

This synthetic matrix is the performance workload.
It is not the 4 x 4 manuscript correctness matrix.

## 3. Target benchmark configuration

The target configuration for the reproducibility run is:

| Parameter | Target |
|---|---:|
| Benchmark ID | QFLPN-1M |
| N | 1,000,000 |
| NNZ | 2,000,000 |
| Warm-up iterations | 5 |
| Measured iterations | 10 |
| Fork/Join threshold | 4096 |
| Fork/Join parallelism | 2 |
| Input vector | x[i] = 1.0 |
| Expected output | y[i] = 1.5 |
| Numerical tolerance | 1.0e-12 |
| Timing method | System.nanoTime() |

The target configuration is not evidence that this configuration
has already been executed.

The values in the CSV row and the associated execution evidence
are authoritative for an actual run.

## 4. Historical exploratory measurement

The repository contains one historical benchmark result.

Its source execution log identifies commit:

`d023783efada8b9820793f98ac553f342cd37a0b`

The recorded configuration and values are:

| Metric | Historical value |
|---|---:|
| Timestamp | 2026-10-20T01:51:18.540403566Z |
| Benchmark ID | QFLPN-1M |
| N | 1,000,000 |
| NNZ | 2,000,000 |
| Warm-up iterations | 1 |
| Measured iterations | 2 |
| Threshold | 4096 |
| Parallelism | 2 |
| Sequential average time | 5.753132 ms |
| Parallel average time | 1.961663 ms |
| Speedup | 2.932783051931 |
| Time reduction | 65.90269439324527% |
| Sequential expected error | 0.0 |
| Parallel expected error | 0.0 |
| Maximum absolute difference | 0.0 |
| CPU architecture | amd64 |
| Available processors | 4 |
| JVM | 21.0.12.1 |
| Operating system | Linux 6.17.0-1022-azure |

The speedup is:

S = 5.753132 / 1.961663
  = 2.932783051931

The time reduction is:

R = 1 - (1.961663 / 5.753132)
  = 0.6590269439324528

R_percent = 65.90269439324527%

The historical independent validator report records:

`"validation": "PASS"`

The historical execution log records:

- 154 Java tests passed;
- 30 Python validator tests passed;
- Maven BUILD SUCCESS;
- independent benchmark validation passed.

These are historical results for the recorded source revision.
They do not validate later source changes.

This historical experiment used 1 warm-up and 2 measured
iterations. It must not be presented as the target 5/10 run.

## 5. Current target run status

The target 5/10 experiment remains pending until a new
execution produces all of the following:

1. a new CSV record;
2. the corresponding complete execution log;
3. the environment report;
4. an independent JSON validation report;
5. a run-specific SHA-256 manifest;
6. successful Java and Python tests on the same source revision.

No target 5/10 speedup is asserted in this document.

## 6. Measurement methodology

The benchmark performs the following operations:

1. Constructs the synthetic CSR matrix.
2. Constructs the input and output vectors.
3. Creates one ForkJoinPool.
4. Executes sequential warm-up iterations.
5. Executes parallel warm-up iterations.
6. Measures sequential CSR multiplication.
7. Measures parallel CSR multiplication using the same pool.
8. Computes average execution times.
9. Computes speedup and throughput.
10. Checks numerical consistency.
11. Persists the result in CSV format.

Pool construction and shutdown are outside the measured SpMV
calls. The setup time is not included in the sequential or
parallel average execution times.

## 7. Performance definitions

Let:

- T_seq = average sequential execution time;
- T_par = average parallel execution time.

Speedup:

S = T_seq / T_par

Execution-time reduction:

R = 1 - (T_par / T_seq)

Percentage reduction:

R_percent = 100 * R

Throughput:

Throughput = N / execution_time_in_seconds

The reduction is not clamped to zero. If parallel execution
is slower than sequential execution, the reduction is negative
and must be reported as a slowdown.

Speedup and reduction must be calculated from the same
measured average execution times.

## 8. Numerical validation

The configured tolerance is:

epsilon = 1.0e-12

The benchmark must check:

- sequential output against the expected value 1.5;
- parallel output against the expected value 1.5;
- maximum absolute difference between sequential and parallel
  output vectors.

A result that fails numerical validation is not an accepted
performance measurement.

## 9. Evidence and provenance

The benchmark CSV is:

`P3/benchmarks/benchmark_results.csv`

Each new execution must preserve its evidence in:

`P3/results/raw/<RUN_ID>/`

The run-specific evidence directory contains:

- `benchmark.log`;
- `environment.txt`;
- `validation-report.json`;
- `SHA256SUMS.txt`.

The SHA-256 manifest also includes the benchmark CSV.

The CSV is append-only. Historical rows must not be manually
rewritten to match a later benchmark configuration.

## 10. Acceptance status

| Criterion | Status |
|---|---|
| Manuscript 4 x 4 dense-oracle correctness | Historical CI PASS |
| CSR implementation | Present |
| Sequential SpMV | Present |
| Parallel SpMV | Present |
| Fork/Join decomposition | Present |
| Historical exploratory benchmark | Recorded |
| Historical independent validation | PASS |
| Target 5/10 benchmark | PENDING |
| Target run-specific evidence | PENDING |
| Target run SHA-256 verification | PENDING |
| CI validation after latest MultiplyTask correction | PENDING |

## 11. Reporting restrictions

The following distinctions are mandatory:

- correctness tests are not performance measurements;
- the synthetic benchmark is not the manuscript 4 x 4 matrix;
- historical 1/2 results are not target 5/10 results;
- CI environment metadata is not local environment metadata;
- estimated array storage is not measured peak memory;
- source-level complexity is not an empirical speedup;
- a target configuration is not proof of execution.

No performance claim for the target 5/10 configuration
is accepted until its corresponding evidence package
has been generated and inspected.
