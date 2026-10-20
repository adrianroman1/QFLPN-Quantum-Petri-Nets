# P3 — Validation Alignment

## 1. Purpose

This document defines the relationship between the
P3 manuscript, mathematical specification, Java
implementation, automated tests, CI evidence and
experimental results.

It complements:

- `P3/results/Traceability.md`;
- `P3/results/Results.md`;
- `P3/results/Reproducibility.md`;
- `P3/P3_AUDIT_REPORT.md`.

It does not replace the detailed manuscript-to-code
mapping in `Traceability.md`.

## 2. Evidence hierarchy

The following evidence levels are distinguished.

| Level | Evidence | What it establishes |
|---|---|---|
| E1 | Manuscript definition | Published mathematical or algorithmic specification |
| E2 | Source code | Presence of an implementation |
| E3 | Unit and integration tests | Behavior covered by executed tests |
| E4 | CI run | Test and build result for an identified commit |
| E5 | Raw benchmark | Actual measured execution |
| E6 | Independent validation | Consistency checks on recorded benchmark data |
| E7 | Reproducibility package | Traceable execution, environment and checksums |

A higher level does not automatically establish
claims outside its scope.

For example, a successful JUnit run does not
establish a large-scale speedup.

## 3. Manuscript-to-implementation alignment

| Manuscript claim | Implementation | Verification | Current status |
|---|---|---|---|
| CSR representation | SparseMatrixCSR.java | CSR unit tests | PASS PRELIMINARY |
| CSR matrix-vector multiplication | SparseMatrixCSR.java | Dense oracle and unit tests | PASS |
| Parallel row decomposition | MultiplyTask.java | Fork/Join tests | PASS PRELIMINARY |
| Sequential SpMV | SparseMatrixCSR.java | Unit tests and dense oracle | PASS |
| Parallel SpMV | SparseMatrixCSR.java | Parallel correctness tests | PASS PRELIMINARY |
| Benchmark construction | BenchmarkRunner.java | Source inspection | IMPLEMENTED |
| Sequential timing | BenchmarkRunner.java | Actual benchmark CSV and log | OPEN |
| Parallel timing | BenchmarkRunner.java | Actual benchmark CSV and log | OPEN |
| Speedup | BenchmarkRunner.java | Independent calculation from CSV | OPEN |
| Time reduction | Derived from measured times | Independent calculation | OPEN |
| CSV persistence | BenchmarkResultWriter.java | Writer tests | CI PASS |
| CSV reading | BenchmarkResultReader.java | Reader tests | CI PASS |
| Benchmark validation | BenchmarkAuditValidator.java | Validator tests | CI PASS |
| Python validation | validate_benchmark.py | Python tests and CI | OPEN |
| Environment provenance | BenchmarkEnvironment.java | Environment record | OPEN |
| Full reproducibility | Results and raw artifacts | Evidence package | OPEN |

## 4. Mathematical and numerical requirements

The benchmark workload uses:

- matrix dimension N;
- number of non-zero entries NNZ;
- CSR representation;
- sequential SpMV;
- parallel SpMV.

For the deterministic synthetic benchmark:

`NNZ = 2N`

The input vector is:

`x[i] = 1.0`

The expected output is:

`y[i] = 1.5`

The synthetic performance workload is distinct
from the 4 x 4 correctness matrix in the manuscript.

The dimension N must not be interpreted as the
number of qubits.

## 5. Performance metric alignment

Let:

- T_seq = measured sequential average time;
- T_par = measured parallel average time.

Speedup:

`S = T_seq / T_par`

Time reduction:

`R = 1 - T_par / T_seq`

Percentage reduction:

`R_percent = 100 * R`

Both metrics must be derived from the same measured
execution and the same CSV record.

A reported speedup is not accepted solely because
the formula is implemented in Java.

## 6. Numerical validation alignment

The configured numerical tolerance is:

`epsilon = 1.0e-12`

The following errors must be finite and nonnegative:

- sequential expected error;
- parallel expected error;
- maximum absolute difference between outputs.

Each must satisfy:

`0.0 <= error <= epsilon`

The Java and Python validation layers must apply
compatible acceptance rules.

A failed numerical check invalidates the associated
performance result.

## 7. Benchmark configuration alignment

The manuscript records the configuration associated
with its reported benchmark.

The Java runner also has default configuration values.
Defaults must not be treated as manuscript evidence.

For every benchmark execution, retain the actual:

- dimension;
- NNZ;
- warm-up count;
- measured iteration count;
- Fork/Join threshold;
- parallelism;
- Java version;
- operating system;
- CPU architecture;
- execution timestamp;
- source commit.

The recorded CSV values are authoritative for
interpreting that execution.

## 8. CI alignment

The inspected CI run:

- commit: `1d0f9895079b614f2dd44fd42ce72583434c0d83`;
- run ID: `39341861788`;
- JUnit tests: 154;
- failures: 0;
- errors: 0;
- skipped: 0;
- Maven build: SUCCESS.

This evidence applies to that commit only.

The current workflow does not execute the Python
validator test suite.

Python validation must be added to CI before
the complete validation pipeline can be marked PASS.

## 9. Experimental evidence alignment

The following files are required for a complete
benchmark evidence package:

| Artifact | Purpose | Status |
|---|---|---|
| `P3/benchmarks/benchmark_results.csv` | Recorded measurements | OPEN |
| `P3/results/raw/` execution log | Full execution output | OPEN |
| `P3/results/raw/` environment report | Runtime and hardware metadata | OPEN |
| Validator output | Independent CSV validation | OPEN |
| Source commit SHA | Source provenance | OPEN |
| `P3/SHA256SUMS.txt` | Integrity checksums | OPEN |

The presence of the benchmark runner or its CSV
writer does not establish that an experiment
has been executed.

## 10. Acceptance rules

A criterion can be marked PASS only if the
available evidence directly supports that criterion.

The following are not interchangeable:

- source implementation and execution;
- correctness testing and performance measurement;
- reported manuscript values and independently reproduced values;
- estimated memory and measured memory;
- CI success and experimental reproducibility.

## 11. Current alignment register

| ID | Criterion | Status |
|---|---|---|
| M3.1 | Provenance | OPEN |
| M3.2 | CSR representation | PASS PRELIMINARY |
| M3.3 | Complexity evidence | OPEN |
| M3.4 | Fork/Join | PASS PRELIMINARY |
| M3.5 | Dense oracle | PASS |
| M3.6 | Speedup | OPEN |
| M3.7 | Time reduction | OPEN |
| M3.8 | Memory accounting | PASS PRELIMINARY |
| M3.9 | Java tests | 154/154 PASS on inspected commit |
| M3.10 | Reproducibility | OPEN |
| M3.11 | Manuscript-code-results alignment | OPEN |
| P3_ACCEPTED | Overall acceptance | OPEN |

## 12. Final statement

P3 has a Java implementation and a successful
154-test CI result on the identified commit.

The large-scale benchmark evidence package is
not yet complete.

The manuscript's performance claims must remain
distinguished from independently reproduced
experimental results until the raw data, execution
environment, validator output and checksums
are available.
