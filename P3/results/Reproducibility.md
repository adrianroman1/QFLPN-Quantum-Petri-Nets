# P3 — Benchmark Reproducibility Protocol

## 1. Objective

This protocol defines the reproducible execution of the P3
large-scale CSR sparse matrix-vector benchmark.

The benchmark uses deterministic matrix and vector construction.

No random-number generator is used.

Therefore:

- random seed: NOT APPLICABLE;
- matrix generation: deterministic;
- input vector: x[i] = 1.0;
- expected output: y[i] = 1.5;
- matrix dimension: N;
- number of non-zero elements: NNZ = 2N.

## 2. Required software

The successful P3 CI validation run used:

| Component | Observed CI version |
|---|---|
| Java distribution | Eclipse Temurin |
| Java version | 21.0.12.1 |
| Maven | 3.10.0 |
| JUnit | 5.10.2 |
| Maven Compiler Plugin | 3.13.0 |
| Maven Surefire Plugin | 3.2.5 |

These are CI environment observations.
They must not be presented as the local benchmark environment.

The local benchmark environment must be captured independently.

## 3. Benchmark configuration

Default reproducibility configuration:

| Parameter | Value |
|---|---:|
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

The benchmark accepts explicit command-line parameters.
The actual parameters stored in the CSV row are authoritative.

## 4. Matrix construction

For each row i, the benchmark creates:

A[i,i] = 1.0

A[i,i+1] = 0.5, when i < N-1

For the final row:

A[N-1,0] = 0.5

Thus, for N > 1:

NNZ = 2N

The input vector is:

x[i] = 1.0

The expected result is:

y[i] = 1.5

This is a deterministic synthetic benchmark matrix.
It is not the 4 x 4 correctness matrix in manuscript Section 13.

## 5. Execution procedure

The canonical execution script is:

`P3/results/run_benchmark.sh`

From the repository root, execute:

```bash
bash P3/results/run_benchmark.sh
