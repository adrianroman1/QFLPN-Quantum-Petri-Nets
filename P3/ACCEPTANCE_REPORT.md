P3 — Acceptance Report

1. Document status

Current decision: PENDING VALIDATION — NOT ACCEPTED

This report defines the evidence required for final P3 acceptance. It must be updated only after the complete CI workflow has run successfully on the candidate commit.

No PASS result is assumed or pre-filled.

2. Candidate identity

Field| Value
Repository| "adrianroman1/QFLPN-Quantum-Petri-Nets"
Branch| "main"
Candidate commit SHA| PENDING
GitHub Actions run ID| PENDING
GitHub Actions run URL| PENDING
Workflow conclusion| PENDING
Java version| 21 (configured)
Python version| 3.12 (configured)

The candidate commit SHA must match the SHA checked out by the workflow.

3. Acceptance gates

ID| Acceptance requirement| Evidence| Status
A01| Root Maven validation| Workflow log| PENDING
A02| Root Maven tests| Surefire reports| PENDING
A03| P3 Maven validation| Workflow log| PENDING
A04| P3 Maven tests| Surefire reports| PENDING
A05| Python validator and integrity tests| Pytest output| PENDING
A06| Python syntax validation| "py_compile" output| PENDING
A07| Benchmark execution| Benchmark run reports| PENDING
A08| Exactly one new benchmark record| CSV evidence| PENDING
A09| Strict V2 CSV validation| Validator JSON report| PENDING
A10| Benchmark JSON/CSV consistency| Summary output| PENDING
A11| Deterministic manifest generation| Generator output| PENDING
A12| Manifest reproducibility| Generator "--check" output| PENDING
A13| Independent SHA-256 verification| Verifier output| PENDING
A14| Evidence artifact retention| GitHub Actions artifact| PENDING
A15| Same-commit evidence identity| Workflow SHA and artifact metadata| PENDING

4. Benchmark configuration

The configured CI benchmark is:

Parameter| Required value
Dimension| 1,000,000
Non-zero values| 2,000,000
Warm-up iterations| 5
Measured iterations| 10
Threshold| 4,096
Parallelism| 2

The actual run ID, measured timings, speedup, throughput, and numerical errors must be copied from the successful run's evidence.

No timing or speedup value is asserted by this template.

5. Required evidence artifacts

The successful workflow must retain:

- "P3/benchmarks/benchmark_results_v2.csv"
- "P3/results/raw/<run-id>/benchmark-report.json"
- "P3/results/raw/<run-id>/benchmark-report.md"
- "P3/results/raw/<run-id>/benchmark-report.txt"
- "P3/results/raw/<run-id>/validation-report.json"
- "P3/MANIFEST.txt"
- "P3/SHA256SUMS.txt"
- root Maven Surefire reports;
- P3 Maven Surefire reports.

The artifact must be linked to the workflow run that validated the candidate commit.

6. Defect and exception register

ID| Description| Severity| Resolution| Status
D01| Missing benchmark summary generator identified during Lot 5 audit| Blocking| Add and validate "generate_benchmark_summary.py"| PENDING CI
D02| Acceptance report absent during Lot 5 audit| Blocking| Add this report| PENDING CI
D03| Historical validation alignment document| Blocking for traceability| Replace with current validation contract| PENDING CI
D04| Automatic evidence push from CI| Integrity/traceability risk| Remove write job; retain artifacts against tested commit| PENDING CI

Additional defects discovered during CI must be recorded here before acceptance.

7. Final decision

The final decision must be exactly one of:

- ACCEPTED — every mandatory gate passed on the same commit and evidence is retained.
- REJECTED — a mandatory gate failed or evidence is inconsistent.
- PENDING VALIDATION — the complete evidence set is not yet available.

Current decision:

PENDING VALIDATION — NOT ACCEPTED

8. Sign-off record

Role| Name / identity| Date| Decision
Implementation| PENDING| PENDING| PENDING
Independent validation| PENDING| PENDING| PENDING
Final acceptance| PENDING| PENDING| PENDING

A final ACCEPTED decision must include the full commit SHA and GitHub Actions run URL.
