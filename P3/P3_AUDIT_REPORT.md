# P3 — Technical Audit Report

## 1. Project identification

**Project:** QFLPN — Quantum-Fuzzy Logical Petri Nets

**Part:** P3 — Sparse Quantum-Fuzzy Logical Petri Nets:
CSR/SpMV Algorithms and Large-Scale State Evolution

**Repository:**
`adrianroman1/QFLPN-Quantum-Petri-Nets`

**Branch:** `main`

**Audit date:** 2026-10-22

**Latest inspected MultiplyTask correction:**
`ff19db6053f19f0c1e650c4fca1c8b1e127399ee`

**Corresponding regression-test update:**
`b68a0e81b98797fc224f6b117e533d80381c2b00`

## 2. Audit scope

The audit covers:

- CSR representation;
- sequential sparse matrix-vector multiplication;
- parallel sparse matrix-vector multiplication;
- Java Fork/Join decomposition;
- rectangular matrix handling;
- numerical validation;
- benchmark CSV persistence;
- independent Python validation;
- automated tests;
- CI workflow;
- benchmark execution evidence;
- checksums;
- manuscript-to-code traceability;
- experimental reproducibility.

The audit distinguishes source inspection, automated
test evidence, CI evidence and experimental measurements.

A source-code correction is not considered validated
until the corresponding test suite has executed on
that source revision.

## 3. Repository evidence correction

An earlier version of this report incorrectly stated
that the following artifacts were absent:

- `P3/benchmarks/benchmark_results.csv`;
- `P3/results/raw/benchmark-QFLPN-1000000.log`;
- `P3/results/raw/environment.txt`;
- `P3/results/validation-report.json`;
- `P3/SHA256SUMS.txt`.

That statement was incorrect.

All five artifacts are present in the inspected
repository and must be treated as historical evidence.

The benchmark CSV contains one historical result.
The corresponding JSON report records independent
validation as PASS.

The evidence must not be described as absent.

## 4. Historical benchmark evidence

The historical execution log identifies source commit:

`d023783efada8b9820793f98ac553f342cd37a0b`

The recorded benchmark is:

| Metric | Value |
|---|---:|
| N | 1,000,000 |
| NNZ | 2,000,000 |
| Warm-up iterations | 1 |
| Measured iterations | 2 |
| Parallelism | 2 |
| Threshold | 4096 |
| Sequential average | 5.753132 ms |
| Parallel average | 1.961663 ms |
| Speedup | 2.932783051931 |
| Time reduction | 65.90269439324527% |
| Sequential expected error | 0.0 |
| Parallel expected error | 0.0 |
| Maximum absolute difference | 0.0 |

The JSON report records:

`"validation": "PASS"`

The historical raw execution log records:

- 154 Java tests passed;
- 30 Python validator tests passed;
- Maven BUILD SUCCESS;
- independent benchmark validation passed.

The SHA-256 manifest records checksums for the
historical CSV, log, environment report and validation JSON.

This is a historical exploratory benchmark using
1 warm-up and 2 measured iterations.

It is not evidence of the target 5/10 configuration.

## 5. Java implementation

The P3 Maven project explicitly uses:

- main source directory: `P3/code`;
- test source directory: `P3/tests`;
- Java release: 21.

The implementation includes:

- `SparseMatrixCSR.java`;
- `MultiplyTask.java`;
- `QFLPNCoreEngine.java`;
- `BenchmarkRunner.java`;
- `BenchmarkResult.java`;
- `BenchmarkResultWriter.java`;
- `BenchmarkResultReader.java`;
- `BenchmarkAuditValidator.java`;
- `BenchmarkEnvironment.java`.

The project compiles the sources under `P3/code`
and the tests under `P3/tests`.

There are additional Java source copies outside
these configured Maven directories. They must be
reconciled separately before claiming that all
repository copies are identical.

## 6. MultiplyTask rectangular-matrix defect

### D01 — Incorrect row-index validation

**Severity:** HIGH

The previous constructor checked:

`startRow > input.length`

This was incorrect.

`startRow` and `endRow` represent row indices.
The input vector length represents the number of
matrix columns.

The output vector length represents the number
of matrix rows.

For a rectangular matrix with more rows than
columns, a valid row index can exceed the input
vector length.

The incorrect check could reject valid Fork/Join
subtasks.

### Correction present in Git

Commit:

`ff19db6053f19f0c1e650c4fca1c8b1e127399ee`

File:

`P3/code/MultiplyTask.java`

The correction removes the invalid comparison
and retains validation against the output vector.

### Regression test present in Git

Commit:

`b68a0e81b98797fc224f6b117e533d80381c2b00`

File:

`P3/tests/MultiplyTaskTest.java`

The replacement test uses a 100-row, 2-column
matrix and checks the Fork/Join result.

### Verification status

The correction and regression test are present
in the inspected Git history.

No CI result associated with the latest correction
commit was returned during this audit.

**Status: IMPLEMENTED — CI VERIFICATION PENDING.**

## 7. Python benchmark validator

The current validator contains explicit nonnegative
checks for:

- `sequential_expected_error`;
- `parallel_expected_error`;
- `max_absolute_error`.

It also checks the upper numerical tolerance.

The validator checks benchmark identity, dimension,
NNZ, configuration, numerical fields, speedup,
throughput and execution metadata.

The historical Python regression suite contains
30 tests, including negative-error rejection tests.

The historical raw execution log records all
30 Python tests passing.

**Status: HISTORICAL TEST EVIDENCE PRESENT.**

A new execution is still required to establish
that the latest repository revision passes the
Python test suite.

## 8. CI workflow

The inspected workflow is:

`.github/workflows/p3-validation.yml`

It includes:

- Maven project validation;
- the Java test suite;
- Python validator regression tests;
- manual benchmark execution;
- benchmark evidence upload;
- JUnit report upload;
- generated evidence commit.

The Python test suite is therefore already integrated
into the inspected workflow.

The earlier statement that Python validation was
not executed by CI was incorrect.

The historical raw benchmark log also confirms
execution of the Python tests.

**Status: IMPLEMENTED — LATEST COMMIT VERIFICATION PENDING.**

## 9. Benchmark evidence traceability

### D04 — Fixed evidence filenames

**Severity:** HIGH for repeated-run traceability

The inspected `run_benchmark.sh` uses fixed paths for:

- benchmark log;
- environment report;
- validation JSON;
- root-level checksum manifest.

Repeated executions can overwrite these files.

The CSV is append-only, but the fixed evidence files
do not preserve a distinct evidence package for each run.

A unique execution identifier and run-specific
evidence directory are required.

**Status: OPEN IN THE INSPECTED SCRIPT.**

The proposed replacement script uses:

`P3/results/raw/<RUN_ID>/`

and stores the execution log, environment, validation
report and SHA-256 manifest there.

This correction is not considered present in Git
until the replacement is uploaded.

## 10. Benchmark configuration alignment

The historical CSV records:

- 1 warm-up iteration;
- 2 measured iterations;
- threshold 4096;
- parallelism 2.

The reproducibility target is:

- 5 warm-up iterations;
- 10 measured iterations;
- threshold 4096;
- parallelism 2.

These configurations must not be conflated.

The historical speedup of approximately 2.93x belongs
only to the historical 1/2 experiment.

**Status: HISTORICAL RESULT VERIFIED; TARGET 5/10 PENDING.**

## 11. Acceptance register

| ID | Criterion | Current status |
|---|---|---|
| M3.1 | Benchmark provenance | Historical evidence present |
| M3.2 | CSR representation | Historical CI PASS |
| M3.3 | Complexity evidence | Documentation present; review required |
| M3.4 | Fork/Join implementation | Present |
| M3.5 | CSR versus dense oracle | Historical CI PASS |
| M3.6 | Historical measured speedup | 2.932783x recorded |
| M3.7 | Historical time reduction | 65.9027% recorded |
| M3.8 | Memory accounting | Source-level estimate only |
| M3.9 | Historical Java tests | 154/154 PASS |
| M3.10 | Historical Python tests | 30/30 PASS |
| M3.11 | Historical reproducibility evidence | Present |
| D01 | Rectangular matrix row validation | Corrected in Git; CI pending |
| D02 | Negative numerical-error validation | Implemented |
| D03 | Python validation in CI | Implemented |
| D04 | Unique evidence per execution | Open in inspected script |
| D05 | Actual benchmark evidence | Historical evidence present |
| M3.12 | Target 5/10 experiment | Pending |
| P3_ACCEPTED | Overall acceptance | NOT GRANTED |

## 12. Required remaining actions

The next validation cycle must:

1. upload the corrected benchmark execution script;
2. upload the workflow with unique run identifiers;
3. preserve historical benchmark artifacts;
4. upload the corrected Results document;
5. upload the corrected Reproducibility document;
6. upload this corrected audit report;
7. execute CI on the resulting source revision;
8. inspect the complete Java test report;
9. inspect the complete Python test report;
10. execute the target 5/10 benchmark;
11. verify the run-specific JSON report;
12. verify all SHA-256 checksums;
13. reconcile duplicate Java source copies;
14. verify manuscript-to-code-to-result consistency.

## 13. Final audit conclusion

P3 has a substantial existing implementation and
historical experimental evidence.

The historical benchmark records a speedup of
2.932783x and a time reduction of 65.9027% under
the recorded 1/2 configuration.

The historical execution also records 154 passing
Java tests and 30 passing Python tests.

The rectangular-matrix defect has been corrected
in the latest inspected Java source and a regression
test has been added.

However, the latest correction has not yet been
verified by a CI execution in the evidence inspected
for this report.

The fixed-name benchmark evidence paths also need
to be replaced by unique per-execution directories.

The target 5/10 benchmark has not yet been established.

**Overall status: P3_ACCEPTED — NOT GRANTED.**
