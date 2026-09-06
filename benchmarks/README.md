# QFLPN CSR Benchmark Results

This directory stores benchmark-related information for the
QFLPN sparse CSR implementation.

## Benchmark output

The executable benchmark is:

`hpc.csr.BenchmarkRunner`

The benchmark reports:

- sequential execution time;
- parallel execution time;
- speedup;
- sequential throughput;
- parallel throughput;
- numerical validation errors;
- setup time;
- CSR memory estimation;
- execution environment metadata.

## GitHub Actions

The CI workflow executes a benchmark smoke run after the
JUnit test suite and CSR smoke validation.

The current CI smoke benchmark uses:

- N = 1,000,000
- warmup = 1
- measured iterations = 2
- threshold = 4096
- parallelism = 2

The benchmark output is printed directly in the GitHub Actions
job log.

## Result persistence

`BenchmarkResultWriter` can persist benchmark measurements to:

`benchmarks/benchmark_results.csv`

The CSV is intended as a persistent research-data log.

The CSV writing operation is performed after the measured CSR
operations and therefore is not included in the reported
sequential or parallel multiplication times.

## Research benchmark policy

CI benchmark values are validation/smoke measurements.

They must not automatically be treated as final doctoral
performance results because GitHub-hosted runners are not a
fixed experimental hardware platform.

Final research measurements should record at least:

- CPU model;
- number of available processors;
- RAM;
- operating system;
- Java version;
- JVM configuration;
- matrix dimension N;
- NNZ;
- warmup iterations;
- measured iterations;
- threshold;
- sequential time;
- parallel time;
- speedup;
- throughput;
- numerical error.

## Target scales

The project currently uses the following benchmark identifiers:

- `QFLPN-12`
- `QFLPN-1M`
- `QFLPN-30M`

The `QFLPN-30M` benchmark is a large-scale research measurement
and should not be executed automatically on every CI push.

## Validation criterion

A benchmark execution is considered numerically valid only when:

`sequentialExpectedError <= 1e-12`

`parallelExpectedError <= 1e-12`

`maxAbsoluteError <= 1e-12`

and all three validation states report `PASS`.
