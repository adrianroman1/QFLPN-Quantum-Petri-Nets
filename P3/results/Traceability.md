# P3 — Requirements and Evidence Traceability

## 1. Purpose

This document maps the mathematical and engineering
requirements of P3 to implementation components, tests,
and execution evidence.

A requirement is not considered verified merely because
a source file or test file exists.

Verification requires an executed test or another
reproducible evidence source.

## 2. Evidence levels

| Level | Meaning |
|---|---|
| E1 | Requirement or mathematical definition documented |
| E2 | Implementation source identified |
| E3 | Relevant automated test implemented |
| E4 | Relevant test executed successfully |
| E5 | Independent numerical or structural validation passed |
| E6 | CI execution and generated artifacts preserved |
| E7 | Final acceptance evidence tied to one commit |

A higher evidence level must not be claimed without
the evidence required by that level.

## 3. CSR requirements

| Requirement | Implementation area | Required verification |
|---|---|---|
| CSR dimensions | SparseMatrixCSR | Constructor and dimension tests |
| Row pointer structure | SparseMatrixCSR | Monotonicity and boundary tests |
| Column index bounds | SparseMatrixCSR | Invalid-index tests |
| Values and indices lengths | SparseMatrixCSR | Structural validation |
| Empty rows | SparseMatrixCSR | Empty-row tests |
| Duplicate columns | SparseMatrixCSR | Duplicate aggregation tests |
| Element lookup | SparseMatrixCSR.get | Independent expected values |
| Matrix-vector multiplication | SparseMatrixCSR.multiply | Dense oracle comparison |

### 3.1 Duplicate-column semantics

For duplicate entries in one row, the mathematical
matrix element is the sum of all entries having
the same column index.

The `get(row, column)` method and SpMV must therefore
implement the same mathematical interpretation.

This requirement must be covered by an explicit regression test.

## 4. SpMV requirements

| Requirement | Implementation area | Required verification |
|---|---|---|
| Sequential SpMV | SparseMatrixCSR | Dense oracle |
| Parallel SpMV | MultiplyTask | Dense oracle |
| Sequential/parallel equivalence | Both implementations | Element-wise comparison |
| Rectangular matrices | CSR and MultiplyTask | Both orientations |
| Empty rows | CSR and MultiplyTask | Explicit fixtures |
| Deterministic generated cases | Test utilities | Repeated deterministic execution |

The dense oracle must be independent of the CSR
multiplication implementation.

## 5. Fork/Join requirements

The Fork/Join implementation must demonstrate:

- correct row interval boundaries;
- correct splitting of task ranges;
- correct handling of small workloads;
- correct handling of uneven row counts;
- no missing output rows;
- no overlapping output ownership that causes races;
- equivalence with sequential SpMV;
- equivalence with the independent dense oracle.

The implementation and tests must be checked in every
maintained source location.

Duplicate source copies must be either intentionally
maintained and verified identical, or replaced by one
authoritative source.

## 6. Benchmark requirements

| Requirement | Implementation area | Required verification |
|---|---|---|
| Warm-up count | BenchmarkRunner | Configuration test |
| Measurement count | BenchmarkRunner | Configuration test |
| Sequential timing | BenchmarkRunner | Result validation |
| Parallel timing | BenchmarkRunner | Result validation |
| Mean and median | BenchmarkResult | Statistical unit tests |
| Dispersion | BenchmarkResult | Statistical unit tests |
| Speedup | BenchmarkResult | Formula test |
| Throughput | BenchmarkResult | Formula test |
| Independent numeric validation | Oracle/test utilities | Numeric comparison |
| Unique run identifier | BenchmarkRunner | Format and uniqueness tests |

Canonical configuration:

```text
warmup_iterations = 5
measured_iterations = 10
matrix_dimension = 1000000
non_zero_elements = 2000000
parallel_threshold = 4096
parallelism = 2
numeric_tolerance = 1e-12
