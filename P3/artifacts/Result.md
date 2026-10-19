# P3 — Experimental Artifact Register

## 1. Purpose

This document records the artifacts supporting the P3
implementation, correctness validation, and performance
measurements.

An artifact is considered available only when its location
and integrity information can be verified.

A test report is not a substitute for a performance benchmark.
A successful CI run does not establish a speedup.

## 2. GitHub Actions validation artifact

Workflow:

`.github/workflows/p3-validation.yml`

Workflow run:

https://github.com/adrianroman1/QFLPN-Quantum-Petri-Nets/actions/runs/39331045606

Run ID:

`39331045606`

Commit:

`16f76d8990d1b1e6d41ce4e14a869a000fea3655`

Job:

`P3 CSR, SpMV and JUnit Validation`

Job ID:

`118329005482`

Conclusion:

`success`

The job executed:

- Maven validate;
- production source compilation;
- test source compilation;
- the complete P3 JUnit suite;
- CSR-versus-dense independent oracle test.

JUnit summary:

```text
Tests run: 126
Failures: 0
Errors: 0
Skipped: 0
BUILD SUCCESS
