# P3 — Acceptance Report

This file is produced by the CI workflow from the current run's artifacts.
It is intentionally conservative and does not claim ACCEPTED unless all mandatory gates have passed on the same commit and the same workflow run.

## Current status

Current decision: PENDING VALIDATION — NOT ACCEPTED

## Evidence identity

- Repository: `adrianroman1/QFLPN-Quantum-Petri-Nets`
- Branch: `main`
- Candidate commit SHA: `PENDING`
- GitHub Actions run ID: `PENDING`
- GitHub Actions run URL: `PENDING`
- Workflow conclusion: `PENDING`
- Java version: `21 (configured)`
- Python version: `3.12 (configured)`

This document is not valid as a final acceptance record until a completed workflow run attaches the real SHA and run URL.

## Mandatory gates

| Gate | Evidence | Status |
| --- | --- | --- |
| Root Maven validation | Workflow log | PENDING |
| Root Maven tests | Surefire reports | PENDING |
| P3 Maven validation | Workflow log | PENDING |
| P3 Maven tests | Surefire reports | PENDING |
| Python validator and integrity tests | Pytest output | PENDING |
| Python syntax validation | `py_compile` output | PENDING |
| Benchmark execution | Benchmark run reports | PENDING |
| Exactly one benchmark record | CSV evidence | PENDING |
| Strict V2 CSV validation | Validator JSON report | PENDING |
| Benchmark JSON/CSV consistency | Summary output | PENDING |
| Deterministic manifest generation | Generator output | PENDING |
| Manifest reproducibility | `--check` output | PENDING |
| Independent SHA-256 verification | Verifier output | PENDING |
| Artifact retention | GitHub Actions artifact | PENDING |
| Same-commit evidence identity | Workflow SHA + artifact metadata | PENDING |

## Final decision rule

Final decision must be exactly one of:

- ACCEPTED — all mandatory gates passed on the same commit and evidence is retained.
- REJECTED — a mandatory gate failed or evidence is inconsistent.
- PENDING VALIDATION — the complete evidence set is not yet available.

Current decision:

PENDING VALIDATION — NOT ACCEPTED

## Sign-off record

| Role | Name / identity | Date | Decision |
| --- | --- | --- | --- |
| Implementation | PENDING | PENDING | PENDING |
| Independent validation | PENDING | PENDING | PENDING |
| Final acceptance | PENDING | PENDING | PENDING |

A final ACCEPTED decision requires the full commit SHA and GitHub Actions run URL from the same workflow run.
