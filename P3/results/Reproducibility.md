```markdown
# P3 — Benchmark Reproducibility Protocol

## 1. Objective

This protocol defines how to reproduce the P3 large-scale
CSR sparse matrix-vector benchmark.

The benchmark is deterministic with respect to matrix
construction and input-vector generation.

No random-number generator is used by the current
BenchmarkRunner implementation.

Therefore:

- random seed: NOT APPLICABLE;
- matrix generation: deterministic;
- input vector: x[i] = 1.0;
- expected output: y[i] = 1.5.

## 2. Required software

The CI validation run used:

| Component | Observed CI version |
|---|---|
| Java distribution | Eclipse Temurin |
| Java version | 21.0.12.1 |
| Maven | 3.10.0 |
| JUnit | 5.10.2 |
| Maven Compiler Plugin | 3.13.0 |
| Maven Surefire Plugin | 3.2.5 |

The local execution environment must be captured separately.
Do not assume that the local machine has the same CPU,
operating system, JVM build, or memory limit as GitHub Actions.

## 3. Primary benchmark parameters

The reproducibility run uses:

```text
N             = 1000000
NNZ           = 2000000
warmup        = 5
iterations    = 10
threshold     = 4096
parallelism   = 2
input         = x[i] = 1.0
expected      = y[i] = 1.5
tolerance     = 1.0e-12
