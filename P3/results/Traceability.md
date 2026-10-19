# P3 — Manuscript, Source Code and Evidence Traceability

## 1. Objective

This document maps P3 manuscript claims to:

1. mathematical definitions;
2. Java implementation;
3. automated tests;
4. CI execution evidence;
5. experimental artifacts.

A source-code mapping alone does not establish that
a performance claim has been experimentally validated.

## 2. Manuscript-to-code mapping

| Manuscript item | Mathematical or algorithmic content | Java implementation | Test or evidence | Status |
|---|---|---|---|---|
| Section 13, Eq. (14) | 4 x 4 sparse matrix A | CSR fixture in CSRvsDenseOracleTest.java | Independent dense oracle | PASS |
| Section 13, Eqs. (15)-(17) | values, col_idx, row_ptr | SparseMatrixCSR.java | Exact CSR array assertions | PASS |
| Section 13, Eqs. (18)-(19) | Matrix-vector result | SparseMatrixCSR.multiply() | Dense oracle comparison | PASS |
| CSR representation | Compressed Sparse Row storage | SparseMatrixCSR.java | SparseMatrixCSRTest.java | CI PASS |
| Sequential SpMV | y = A*x | SparseMatrixCSR.multiplyInto() | CSRvsDenseOracleTest.java and unit tests | CI PASS |
| Parallel SpMV | Row-parallel multiplication | SparseMatrixCSR.multiplyParallelInto() | Existing parallel tests | CI PASS |
| Fork/Join decomposition | Recursive row-range splitting | MultiplyTask.java | MultiplyTaskTest.java | CI PASS |
| Synthetic matrix generation | Deterministic matrix with NNZ=2N | BenchmarkRunner.createBenchmarkMatrix() | Source inspection | IMPLEMENTED |
| Input vector | x[i]=1.0 | BenchmarkRunner.createInputVector() | Benchmark numerical validation | IMPLEMENTED |
| Expected synthetic output | y[i]=1.5 | BenchmarkRunner numerical checks | Benchmark execution required | IMPLEMENTED |
| Sequential timing | System.nanoTime() | BenchmarkRunner.measureSequential() | Raw benchmark log and CSV | PENDING |
| Parallel timing | System.nanoTime() | BenchmarkRunner.measureParallel() | Raw benchmark log and CSV | PENDING |
| Speedup | S=T_seq/T_par | BenchmarkRunner.calculateSpeedup() | Raw CSV and independent calculation | PENDING |
| Time reduction | R=1-T_par/T_seq | Derived from measured CSV values | Results.md and raw CSV | PENDING |
| Result persistence | CSV output | BenchmarkResultWriter.java | BenchmarkResultWriterTest.java | CI PASS |
| Environment metadata | JVM, OS, CPU-visible properties | BenchmarkRunner.java and BenchmarkEnvironment.java | Environment capture | PARTIAL |
| Reproducibility | Exact command and environment | Reproducibility.md and run_benchmark.sh | Raw log, environment, SHA-256 | PENDING |

## 3. CSR representation and storage complexity

Let:

- N = number of matrix rows;
- M = number of matrix columns;
- NNZ = number of stored non-zero entries.

The CSR representation stores:

- values: NNZ elements;
- columnIndices: NNZ elements;
- rowPointers: N+1 elements.

Therefore, matrix storage is:

O(N + NNZ)

For a square matrix, the input and output vectors
require an additional O(N) storage.

The total storage requirement remains:

O(N + NNZ)

The constructor performs defensive copies of the CSR arrays.
This requires O(N + NNZ) additional time and temporary storage
during construction.

The implementation uses Java heap arrays.
It does not establish off-heap or GPU memory usage.

## 4. Sequential SpMV complexity

The sequential implementation iterates over all rows.

For each row, it traverses the CSR interval:

rowPointers[row] ... rowPointers[row+1]

Every stored non-zero element is visited once.

The row traversal contributes O(N).

The non-zero traversal contributes O(NNZ).

Therefore:

T_seq = O(N + NNZ)

The bound is stated in its general form.
For common sparse matrices with NNZ >= N, it is also
frequently expressed as O(NNZ).

## 5. Parallel SpMV complexity

The parallel implementation partitions row intervals
using Fork/Join tasks.

The total arithmetic work remains:

O(N + NNZ)

Parallel execution adds task creation, splitting,
scheduling, and synchronization overhead.

The actual elapsed time depends on:

- N;
- NNZ;
- sparsity distribution;
- Fork/Join threshold;
- configured parallelism;
- CPU architecture;
- JVM runtime;
- memory bandwidth;
- scheduling overhead.

The work complexity does not establish a speedup.

Speedup must be established experimentally from
the recorded sequential and parallel execution times.

## 6. Fork/Join row independence

The Fork/Join implementation splits a row interval
into two disjoint subintervals.

Left interval:

[startRow, middle)

Right interval:

[middle, endRow)

The intervals do not overlap.

Each task writes output rows belonging to its own interval.

This design prevents two tasks from writing the same
output row, provided the recursive partition remains disjoint.

Source:

`P3/code/MultiplyTask.java`

Tests:

`P3/tests/MultiplyTaskTest.java`

CI execution proves that the existing JUnit tests passed.
It is not presented as a separate formal concurrency proof.

## 7. Manuscript correctness oracle

The independent dense oracle uses the matrix in
Section 13, equation (14).

The test explicitly defines:

x = (1, 2, 3, 4)^T

The expected vector is:

y = (12, 6, 16, 30)^T

The selected input vector is a test fixture.
The manuscript defines x symbolically.

The test checks:

- CSR values;
- CSR column indices;
- CSR row pointers;
- matrix dimensions;
- NNZ;
- independent dense multiplication;
- sequential CSR multiplication;
- parallel CSR multiplication.

Source:

`P3/tests/CSRvsDenseOracleTest.java`

This correctness test does not constitute a
large-scale performance benchmark.

## 8. Large-scale benchmark distinction

The performance benchmark uses a deterministic synthetic
matrix generated by:

`BenchmarkRunner.createBenchmarkMatrix(int n)`

For N > 1:

NNZ = 2N

The input vector is:

x[i] = 1.0

The expected output is:

y[i] = 1.5

The synthetic matrix must not be identified as the
4 x 4 manuscript correctness matrix.

## 9. Speedup and time reduction

Let:

T_seq = measured average sequential time

T_par = measured average parallel time

Speedup:

S = T_seq / T_par

Time reduction:

R = 1 - T_par / T_seq

The same measured averages must be used in both calculations.

The stored CSV speedup is independently checked by:

`P3/results/validate_benchmark.py`

No speedup or reduction claim is accepted without
the corresponding raw CSV row.

## 10. Memory model

For the synthetic benchmark:

NNZ = 2N

CSR arrays require:

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

The benchmark also creates defensive copies of the
three CSR arrays in the SparseMatrixCSR constructor.

The source-level estimate excludes:

- Java object headers;
- array headers;
- JVM metadata;
- thread stacks;
- ForkJoin task objects;
- runtime allocation overhead;
- garbage collector overhead.

The printed estimate is therefore a model of array
storage, not a measured peak resident memory value.

## 11. CI evidence

Workflow:

`.github/workflows/p3-validation.yml`

Latest inspected run:

https://github.com/adrianroman1/QFLPN-Quantum-Petri-Nets/actions/runs/39332171230

Commit:

`59a45ec375f5b53b9bb466180d8e345044ee7978`

Job:

`P3 CSR, SpMV and JUnit Validation`

Observed result:

```text
Tests run: 126
Failures: 0
Errors: 0
Skipped: 0
BUILD SUCCESS
