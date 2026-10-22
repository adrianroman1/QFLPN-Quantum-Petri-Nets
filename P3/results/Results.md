# P3 — Results and Validation Report

## 1. Purpose

This document records the mathematical validation, automated test
results, benchmark measurements, and execution evidence for P3.

Only results produced by an identifiable execution and supported by
logs or generated artifacts may be reported as verified results.

Historical measurements must not be presented as current measurements.

## 2. Current validation status

Current repository branch: `main`

Inspected commit:

`ede294d4dd27540c644152f5d10ea2fdf070f4dc`

GitHub Actions run:

https://github.com/adrianroman1/QFLPN-Quantum-Petri-Nets/actions/runs/39782076021

Workflow run: #111

### 2.1 Execution results

| Validation stage | Result |
|---|---|
| Root Maven validation and tests | PASS |
| Root Java tests | 143 tests, zero failures |
| P3 Maven validation | PASS |
| P3 Maven compilation/test phase | FAIL |
| Python P3 validation | SKIPPED |
| P3 benchmark execution | SKIPPED |
| Benchmark CSV validation | SKIPPED |
| Manifest generation and verification | SKIPPED |
| Artifact upload | SKIPPED |
| Automated evidence commit | SKIPPED |

### 2.2 Confirmed blocking error

The P3 build failed in:

`P3/code/BenchmarkResultReader.java`

The compiler reported that the `BenchmarkResult` constructor
requires 29 arguments, while the reader supplies 24.

This is a confirmed build failure for workflow run #111.

The benchmark and integrity stages were not reached. Their status
must therefore be reported as NOT RUN, not PASS.

## 3. Mathematical reference fixture

The following deterministic fixture is suitable for independent
CSR and SpMV validation.

Matrix:

```text
A =
[4  0  0  2]
[0  3  0  0]
[1  0  5  0]
[0  0  2  6]
