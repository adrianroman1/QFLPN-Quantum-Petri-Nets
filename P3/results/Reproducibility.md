# P3 — Benchmark Reproducibility Protocol

## 1. Objective

This protocol defines the reproducible execution of the P3
large-scale CSR sparse matrix-vector benchmark.

The benchmark uses deterministic matrix and vector construction.
No random-number generator is used.

The protocol separates:

1. correctness validation using the manuscript's 4 x 4 matrix;
2. large-scale performance measurement using a synthetic matrix;
3. environment capture;
4. independent validation of persisted benchmark results.

A successful correctness test does not establish a performance
claim. Performance claims require an actual benchmark execution
and its corresponding result artifacts.

## 2. Deterministic benchmark definition

The large-scale synthetic benchmark is defined as follows.

For each row i:

A[i,i] = 1.0

A[i,i+1] = 0.5, when i < N-1

For the final row:

A[N-1,0] = 0.5

For N > 1:

NNZ = 2N

The input vector is:

x[i] = 1.0

The expected output is:

y[i] = 1.5

The matrix is deterministic. A random seed is therefore
NOT APPLICABLE.

This synthetic matrix is not the 4 x 4 correctness matrix
defined in manuscript Section 13.

## 3. Required software

The previously inspected successful P3 CI validation run
reported the following environment:

| Component | Observed CI version |
|---|---|
| Java distribution | Eclipse Temurin |
| Java version | 21.0.12.1 |
| Maven | 3.10.0 |
| JUnit | 5.10.2 |
| Maven Compiler Plugin | 3.13.0 |
| Maven Surefire Plugin | 3.2.5 |

These are observations from the CI run, not a declaration
of the local execution environment.

Every local benchmark execution must capture its own
environment metadata.

The benchmark environment includes JVM-visible information:
CPU architecture, available processors, JVM version,
JVM name, operating system, and operating-system version.

## 4. Default benchmark configuration

The documented target configuration is:

| Parameter | Value |
|---|---:|
| Dimension N | 1,000,000 |
| Non-zero elements NNZ | 2,000,000 |
| Warm-up iterations | 5 |
| Measured iterations | 10 |
| Fork/Join threshold | 4096 |
| Fork/Join parallelism | 2 |
| Input vector | x[i] = 1.0 |
| Expected output | y[i] = 1.5 |
| Numerical tolerance | 1.0e-12 |
| Timing method | System.nanoTime() |

The actual command-line configuration used by a benchmark
execution is authoritative. The values persisted in the
CSV result must be used when interpreting that execution.

Do not report the default configuration as the actual
configuration unless the recorded result confirms it.

## 5. Correctness matrix

The manuscript correctness fixture is:

A =

[ 4  0  0  2 ]
[ 0  3  0  0 ]
[ 1  0  5  0 ]
[ 0  0  2  6 ]

Its CSR representation is:

values = (4, 2, 3, 1, 5, 2, 6)

col_idx = (0, 3, 1, 0, 2, 2, 3)

row_ptr = (0, 2, 3, 5, 7)

For the test input:

x = (1, 2, 3, 4)^T

the expected output is:

y = (12, 6, 16, 30)^T

This fixture validates the CSR representation and
matrix-vector multiplication against an independent
dense oracle.

It must not be substituted for the large-scale synthetic
performance benchmark.

## 6. Execution procedure

The canonical execution script is:

`P3/results/run_benchmark.sh`

From the repository root, execute:

```bash
bash P3/results/run_benchmark.sh
```

The script is responsible for orchestrating the P3
validation and benchmark procedure.

Run it from the repository root so that its relative
paths resolve as intended.

Do not manually edit generated benchmark measurements.

## 7. Expected result artifacts

The benchmark result is persisted under:

`P3/benchmarks/benchmark_results.csv`

The independent validator is:

`P3/results/validate_benchmark.py`

The execution procedure also maintains evidence under
the P3 results and artifacts directories.

The exact artifacts produced by an execution must be
verified from the actual filesystem and execution log.
Their presence must not be inferred from this protocol.

The CSV schema contains 22 fields:

1. timestamp;
2. benchmark_id;
3. dimension;
4. non_zero_count;
5. parallelism;
6. threshold;
7. warmup_iterations;
8. measured_iterations;
9. sequential_ms;
10. parallel_ms;
11. speedup;
12. sequential_throughput_states_per_s;
13. parallel_throughput_states_per_s;
14. sequential_expected_error;
15. parallel_expected_error;
16. max_absolute_error;
17. setup_time_ms;
18. cpu;
19. available_memory_bytes;
20. java_version;
21. operating_system;
22. notes.

## 8. Independent result validation

Run the validator from the repository root:

```bash
python P3/results/validate_benchmark.py
```

The validator checks:

- CSV header and field structure;
- existence of benchmark data;
- ISO-8601 timestamp with timezone;
- expected matrix dimension;
- NNZ = 2N;
- configured parallelism;
- configured Fork/Join threshold;
- warm-up and measured iteration counts;
- finite, positive sequential and parallel times;
- consistency of stored speedup;
- consistency of sequential throughput;
- consistency of parallel throughput;
- numerical error limits;
- execution environment metadata.

The validator reports the time reduction as:

R = 1 - T_parallel / T_sequential

The reduction is derived from the same measured times
used to calculate speedup.

A validator PASS confirms the checks implemented by
the validator for the selected CSV row. It does not
independently prove that the benchmark implementation
is free of all defects.

## 9. Performance definitions

Let:

T_seq = measured average sequential execution time

T_par = measured average parallel execution time

Speedup:

S = T_seq / T_par

Time reduction:

R = 1 - T_par / T_seq

Percentage time reduction:

R_percent = 100 * R

Throughput:

Throughput = N / execution_time_in_seconds

Speedup and time reduction must be calculated from
the same benchmark execution and the same recorded
average execution times.

A speedup greater than one indicates that the measured
parallel execution was faster than the sequential
execution for that particular environment and
configuration.

A speedup result must not be generalized to other
hardware or configurations without additional evidence.

## 10. Numerical acceptance

The configured numerical tolerance is:

epsilon = 1.0e-12

The benchmark must reject a result if:

- the sequential output differs from the expected output
  beyond the configured tolerance;
- the parallel output differs from the expected output
  beyond the configured tolerance;
- the sequential and parallel outputs differ beyond
  the configured tolerance.

A numerically invalid benchmark result must not be
accepted as a performance measurement.

Failed numerical validation must occur before a result
is persisted as an accepted benchmark result.

## 11. Memory accounting

For the synthetic benchmark with NNZ = 2N, the principal
CSR array storage is:

values:
2N * 8 bytes

columnIndices:
2N * 4 bytes

rowPointers:
(N+1) * 4 bytes

Input vector:
N * 8 bytes

Output vector:
N * 8 bytes

The implementation may also create defensive copies
of CSR arrays and allocate task and runtime objects.

A source-level array estimate does not represent
measured peak resident memory.

Unless a separate measurement is recorded, do not
describe the array estimate as measured RAM consumption.

The JVM maximum heap value is environment metadata.
It is not equivalent to current free physical memory.

## 12. Evidence and reproducibility requirements

For each accepted performance result, retain:

1. exact source revision or commit SHA;
2. exact execution command;
3. complete execution log;
4. benchmark CSV;
5. environment information;
6. independent validator output;
7. SHA-256 checksums of the retained evidence files;
8. test results from the corresponding source revision.

The evidence must identify which source revision produced
the benchmark result.

A CI test result from a different commit must not be
presented as validation of a later untested modification.

## 13. Reporting restrictions

The following distinctions are mandatory:

- correctness tests are not performance measurements;
- synthetic benchmark results are not results for the
  manuscript's 4 x 4 correctness fixture;
- CI environment metadata is not local environment metadata;
- source-level complexity is not an empirical speedup;
- estimated array storage is not measured peak memory;
- a benchmark configuration is not proof that the
  configuration was actually executed.

Until a real benchmark CSV and its validation output
are available, speedup and time reduction remain
PENDING.
