# P3 — Technical Audit Report

## 1. Project identification

**Project:** QFLPN — Quantum-Fuzzy Logical Petri Nets

**Part:** P3 — Sparse Quantum-Fuzzy Logical Petri Nets:
CSR/SpMV Algorithms and Large-Scale State Evolution

**Repository:**  
`adrianroman1/QFLPN-Quantum-Petri-Nets`

**Last verified CI commit:**  
`1d0f9895079b614f2dd44fd42ce72583434c0d83`

**Audit date:** 2026-10-20

## 2. Audit scope

The audit covers:

- CSR representation;
- sequential sparse matrix-vector multiplication;
- parallel sparse matrix-vector multiplication;
- Java Fork/Join decomposition;
- numerical validation;
- benchmark CSV persistence;
- independent Python validation;
- automated tests;
- CI workflow;
- manuscript-to-code traceability;
- experimental reproducibility.

The audit distinguishes implementation evidence,
automated test evidence and experimental measurement evidence.

## 3. Verified CI evidence

Workflow:

`.github/workflows/p3-validation.yml`

Workflow run:

https://github.com/adrianroman1/QFLPN-Quantum-Petri-Nets/actions/runs/39341861788

Commit:

`1d0f9895079b614f2dd44fd42ce72583434c0d83`

Observed result:

| Metric | Result |
|---|---:|
| JUnit tests | 154 |
| Failures | 0 |
| Errors | 0 |
| Skipped | 0 |
| Maven build | SUCCESS |

The successful CI execution confirms that the Java
validation suite passed on the identified commit.

It does not establish that the large-scale benchmark
was executed.

## 4. Java implementation

The following implementation components are present:

- `SparseMatrixCSR.java`
- `MultiplyTask.java`
- `QFLPNCoreEngine.java`
- `BenchmarkRunner.java`
- `BenchmarkResult.java`
- `BenchmarkResultWriter.java`
- `BenchmarkResultReader.java`
- `BenchmarkAuditValidator.java`
- `BenchmarkEnvironment.java`

The Java implementation covers CSR storage,
sequential and parallel SpMV, benchmark execution,
result persistence and validation.

The source-code presence must not be interpreted
as experimental execution evidence.

## 5. Automated test evidence

The successful CI run reported:

| Test class | Tests |
|---|---:|
| MultiplyTaskTest | 21 |
| BenchmarkResultWriterTest | 6 |
| BenchmarkAuditValidatorTest | 12 |
| BenchmarkResultReaderTest | 13 |
| BenchmarkScaleTest | 9 |
| BenchmarkRunnerNumericalValidationTest | 9 |
| BenchmarkEnvironmentTest | 7 |
| BenchmarkResultTest | 11 |
| QFLPNCoreEngineTest | 33 |
| SparseMatrixCSRTest | 32 |
| CSRvsDenseOracleTest | 1 |
| **Total** | **154** |

All 154 tests passed in the inspected CI run.

## 6. Confirmed validation gaps

### D02 — Python validator accepts negative numerical errors

**Severity:** MEDIUM

The Python validator checks:

- `sequential_expected_error <= EPSILON`;
- `parallel_expected_error <= EPSILON`;
- `max_absolute_error <= EPSILON`.

It does not explicitly require these values to be
nonnegative.

A negative value can therefore satisfy the upper-bound
comparison.

The validator must enforce:

`0.0 <= error <= EPSILON`

for all three numerical error fields.

The corresponding negative-value regression tests
must be executed.

**Status:** OPEN until the correction and tests are
present in the repository and verified.

### D03 — Python validator tests are not executed by CI

**Severity:** HIGH

The current workflow executes Maven validation and
the Java JUnit test suite.

It does not execute:

- `P3/results/test_validate_benchmark.py`;
- the independent Python CSV validator.

The Python validation layer therefore does not have
CI evidence from the inspected workflow.

**Status:** OPEN.

### D04 — Benchmark execution artifacts use fixed filenames

**Severity:** HIGH for experimental traceability

The current `run_benchmark.sh` uses fixed names for
the execution log and environment report.

Repeated executions can overwrite previous evidence.

The benchmark CSV is appended to, while the log and
environment files are not independently versioned
per execution.

This weakens the association between a CSV record
and its corresponding execution evidence.

**Status:** OPEN.

### D05 — Experimental evidence package is absent

**Severity:** HIGH for reproducibility claims

The following expected files were not found at the
inspected Git paths:

- `P3/benchmarks/benchmark_results.csv`;
- `P3/results/raw/benchmark-QFLPN-1000000.log`;
- `P3/results/raw/environment.txt`.

`P3/artifacts/Result.md` exists, but it is not a
complete experimental evidence package.

Consequently, no new large-scale benchmark result
can be independently verified from the repository.

**Status:** OPEN.

## 7. Manuscript and benchmark configuration

The manuscript records a benchmark configuration
including:

- N = 1,000,000;
- NNZ = 2,000,000;
- warm-up iterations = 1;
- measured iterations = 2;
- threshold = 4096;
- parallelism = 2.

The current Java implementation has defaults that
differ from the manuscript configuration.

A benchmark execution must explicitly record the
configuration actually used.

The manuscript's reported values must not be
replaced by Java defaults or by a future target
configuration.

**Status:** OPEN pending evidence linking the
manuscript configuration to an actual benchmark run.

## 8. Structural documentation

The following P3 documents exist:

- `P3/results/Results.md`;
- `P3/results/Reproducibility.md`;
- `P3/results/Traceability.md`;
- `P3/artifacts/Result.md`.

The following structural documents were absent
at the inspected paths:

- `P3/MANIFEST.txt`;
- `P3/SHA256SUMS.txt`;
- `P3/P3_AUDIT_REPORT.md`;
- `P3/VALIDATION_ALIGNMENT.md`.

This report supplies the audit document.
The remaining files must be added and generated
according to their respective procedures.

## 9. Acceptance register

| ID | Criterion | Status |
|---|---|---|
| M3.1 | Benchmark provenance | OPEN |
| M3.2 | CSR representation | PASS PRELIMINARY |
| M3.3 | Complexity evidence | OPEN |
| M3.4 | Fork/Join implementation and tests | PASS PRELIMINARY |
| M3.5 | CSR versus dense oracle | PASS |
| M3.6 | Measured speedup | OPEN |
| M3.7 | Measured time reduction | OPEN |
| M3.8 | Memory accounting | PASS PRELIMINARY |
| M3.9 | Java automated tests | 154/154 PASS on inspected commit |
| M3.10 | Reproducibility package | OPEN |
| M3.11 | Manuscript-code-results alignment | OPEN |
| D02 | Python negative-error validation | OPEN |
| D03 | Python validation in CI | OPEN |
| D04 | Unique benchmark evidence per execution | OPEN |
| D05 | Actual benchmark evidence | OPEN |
| P3_ACCEPTED | Overall acceptance | OPEN |

## 10. Audit conclusion

The inspected Java CI run provides evidence of a
successful 154-test validation on the identified commit.

It does not establish that the large-scale performance
experiment has been reproduced.

The principal remaining work concerns:

1. correcting and testing the Python validator;
2. integrating Python validation into CI;
3. preserving unique execution evidence;
4. producing a real benchmark CSV and raw execution log;
5. recording the actual execution environment;
6. generating checksums for the final evidence;
7. completing manuscript-code-results alignment.

No performance claim should be upgraded to PASS
without the corresponding experimental evidence.

**Overall status: P3_ACCEPTED — OPEN.**
