```markdown
# P3 — Manuscript, Source Code and Evidence Traceability

## 1. Objective

This document maps the mathematical definitions and
algorithmic claims in the P3 manuscript to their Java
implementation, tests, and available execution evidence.

A mapping does not automatically establish acceptance.
Each claim must be supported by the corresponding test,
analysis, or measured artifact.

## 2. Manuscript-to-code mapping

| Manuscript item | Mathematical or algorithmic content | Java implementation | Test or evidence | Status |
|---|---|---|---|---|
| Section 13, Eq. (14) | 4 x 4 sparse matrix A | CSR fixture in CSRvsDenseOracleTest.java | Independent dense oracle | PASS |
| Section 13, Eqs. (15)-(17) | values, col_idx, row_ptr | SparseMatrixCSR.java | Exact CSR array assertions | PASS |
| Section 13, Eqs. (18)-(19) | Matrix-vector result | SparseMatrixCSR.multiply() | Dense oracle comparison | PASS |
| CSR representation | Compressed Sparse Row storage | SparseMatrixCSR.java | SparseMatrixCSRTest.java | CI PASS |
| Sequential SpMV | y = A*x | SparseMatrixCSR.multiplyInto() | CSRvsDenseOracleTest.java and existing unit tests | CI PASS |
| Parallel SpMV | Row-parallel multiplication | SparseMatrixCSR.multiplyParallelInto() | Existing parallel tests | CI PASS |
| Fork/Join decomposition | Recursive row-range splitting | MultiplyTask.java | MultiplyTaskTest.java | CI PASS |
| Large-scale matrix generation | Deterministic synthetic matrix with NNZ=2N | BenchmarkRunner.createBenchmarkMatrix() | Benchmark execution required | IMPLEMENTED |
| Input-vector generation | x[i]=1.0 | BenchmarkRunner.createInputVector() | Benchmark numerical validation | IMPLEMENTED |
| Expected synthetic output | y[i]=1.5 | BenchmarkRunner numerical checks | Benchmark execution required | IMPLEMENTED |
| Sequential timing | System.nanoTime() | BenchmarkRunner.measureSequential() | Raw benchmark log and CSV | PENDING |
| Parallel timing | System.nanoTime() | BenchmarkRunner.measureParallel() | Raw benchmark log and CSV | PENDING |
| Speedup | S=T_seq/T_par | BenchmarkRunner.calculateSpeedup() | Raw CSV and independent calculation | PENDING |
| Time reduction | R=1-T_par/T_seq | Derived from measured CSV values | Results.md and raw CSV | PENDING |
| Result persistence | CSV output | BenchmarkResultWriter.java | BenchmarkResultWriterTest.java | CI PASS |
| Environment metadata | JVM, OS, CPU-visible properties | BenchmarkEnvironment.java and BenchmarkRunner.java | Environment capture | PARTIAL |
| Reproducibility | Exact command and environment | Reproducibility.md | Raw log, environment file, SHA-256 | PENDING |

## 3. CSR storage complexity

Let:

- N be the number of matrix rows;
- M be the number of matrix columns;
- NNZ be the number of stored non-zero entries.

The CSR representation stores:

- values: NNZ elements;
- columnIndices: NNZ elements;
- rowPointers: N+1 elements.

Therefore, the matrix storage requirement is:

O(NNZ + N)

For a square matrix where N=M, the input and output vectors
require an additional O(N) storage.

The total storage requirement for the matrix and vectors is:

O(N + NNZ)

The constructor performs defensive copies of the three CSR
arrays. This is also O(N + NNZ) time and storage during
construction.

## 4. Sequential SpMV complexity

The sequential implementation iterates over every matrix row.

For each row, it traverses the stored CSR entries between:

rowPointers[row] and rowPointers[row+1]

Every stored non-zero entry is visited once.

The row loop contributes O(N), and the non-zero traversal
contributes O(NNZ).

Therefore:

T_seq = O(N + NNZ)

For a square sparse matrix with at least one stored entry
per row, this is commonly written as O(NNZ), but the
general expression is O(N + NNZ).

## 5. Parallel SpMV complexity

The parallel implementation partitions row intervals
using Fork/Join tasks.

Each row is assigned to one task interval. Each output
row is written independently by the task responsible
for that row.

The total arithmetic work remains:

O(N + NNZ)

The parallel implementation introduces task scheduling,
splitting, and synchronization overhead.

The observed elapsed time depends on:

- matrix size;
- sparsity distribution;
- Fork/Join threshold;
- parallelism;
- CPU architecture;
- JVM runtime;
- memory bandwidth;
- scheduling overhead.

The theoretical work bound must not be confused with
a measured speedup claim.

## 6. Fork/Join independence

`MultiplyTask.compute()` splits a row interval into
two disjoint subintervals.

The left task receives:

[startRow, middle)

The right task receives:

[middle, endRow)

The intervals do not overlap.

Each task writes only output rows inside its own interval.

This design avoids concurrent writes to the same output
row, provided the task partitioning remains disjoint.

The corresponding source is:

`P3/code/MultiplyTask.java`

The corresponding test class is:

`P3/tests/MultiplyTaskTest.java`

The CI run executed the P3 test suite successfully.
A separate formal concurrency proof is not claimed by
the JUnit result alone.

## 7. Speedup and reduction traceability

For measured average times:

S = T_seq / T_par

R = 1 - T_par / T_seq

The speedup is stored in the benchmark CSV.

The time reduction is derived from the same CSV row.

The two values must satisfy:

R = 1 - 1/S

up to floating-point rounding.

No speedup or reduction value is accepted without
the underlying sequential and parallel measurements.

## 8. Evidence hierarchy

Evidence is classified as follows:

1. Source inspection:
   establishes what the code currently implements.

2. Unit test:
   establishes the behavior exercised by that test.

3. CI execution:
   establishes that the test was compiled, discovered,
   and executed in the recorded workflow run.

4. Raw benchmark output:
   establishes the measured values for one execution.

5. Independent reproduction:
   establishes that the measurement procedure can be
   repeated under a separately recorded execution.

A higher evidence level does not remove the need to
preserve the lower-level source and configuration.

## 9. Current CI evidence

Workflow:

`.github/workflows/p3-validation.yml`

Run:

https://github.com/adrianroman1/QFLPN-Quantum-Petri-Nets/actions/runs/39331045606

Commit:

`16f76d8990d1b1e6d41ce4e14a869a000fea3655`

Observed test result:

```text
Tests run: 126
Failures: 0
Errors: 0
Skipped: 0
BUILD SUCCESS
