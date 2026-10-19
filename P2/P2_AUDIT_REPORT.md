# QFLPN P2 — Technical Audit Report

**Status:** Audit specification and evidence register  
**Scope:** P2 source code, tests, validation tools and CI  
**Evidence policy:** No PASS status without an inspectable execution artifact

---

## 1. Audit objective

The objective is to assess whether the P2 implementation is:

1. structurally consistent;
2. numerically well-defined;
3. robust against malformed inputs;
4. independently testable;
5. traceable through reproducible validation artifacts.

The audit distinguishes implementation correctness from manuscript-level mathematical validity.

## 2. Scope

The audit covers:

- canonical NumPy reference implementation;
- four-qubit rotation operator;
- controlled-X transition operator;
- transition ordering;
- state-vector normalization;
- density-matrix construction;
- reduced density-matrix calculations;
- PennyLane circuit comparison;
- test execution;
- report validation;
- SHA-256 integrity verification;
- continuous integration.

## 3. Verification categories

### 3.1 Structural verification

Required checks:

- source files exist at their documented paths;
- imports resolve;
- public functions expose the expected interfaces;
- Hilbert-space dimensions are consistent;
- operator multiplication order is explicit.

### 3.2 Numerical verification

Required checks:

- activation values are finite and belong to the permitted interval;
- invalid values are rejected;
- state vectors have the expected dimension;
- state vectors are normalized;
- operators preserve the norm;
- density matrices are Hermitian;
- density matrices have unit trace;
- density matrices are positive semidefinite within a documented tolerance.

### 3.3 Independent circuit comparison

The PennyLane implementation must be executed in an environment
where PennyLane is installed.

The comparison must record:

- exact activation vector;
- simulator and dependency versions;
- state-vector comparison;
- fidelity;
- maximum amplitude difference;
- process exit code.

A skipped PennyLane test is not evidence of independent circuit agreement.

### 3.4 Integrity verification

The final source tree must have a generated SHA-256 manifest.

Verification must reject:

- missing files;
- modified files;
- malformed digests;
- duplicate paths;
- absolute paths;
- parent-directory traversal.

## 4. Evidence register

| ID | Requirement | Required evidence |
|---|---|---|
| P2-A01 | Activation validation | Test output |
| P2-A02 | Four-qubit dimensions | Test output |
| P2-A03 | RY operator construction | Test output |
| P2-A04 | C3X permutation structure | Test output |
| P2-A05 | Transition ordering | Test output |
| P2-A06 | Unitarity | Numerical residuals |
| P2-A07 | State normalization | Numerical residuals |
| P2-A08 | Density-matrix properties | Eigenvalue and trace results |
| P2-A09 | Reduced-state calculation | Independent test output |
| P2-A10 | Adversarial input handling | Test output |
| P2-A11 | PennyLane comparison | Actual simulator execution |
| P2-A12 | Report validation | Validator output |
| P2-A13 | SHA-256 integrity | Manifest and verifier output |
| P2-A14 | CI execution | Workflow run and logs |

## 5. Acceptance rules

A requirement may be marked PASS only when:

1. the relevant command has been executed;
2. its raw output is preserved;
3. the exit code is available;
4. the output corresponds to the reviewed source revision;
5. no unresolved failure affects that requirement.

A test that was not executed must be marked NOT RUN.

A skipped test must be marked SKIPPED, with its reason.

A failed test must remain FAIL until a correction is made and
the affected test is rerun.

## 6. Limitations

Passing software tests does not prove every theorem or proposition
in the P2 manuscript.

Manuscript equations, assumptions, operator definitions and
scientific interpretations require a separate mathematical review.

Performance claims require dedicated measurements and an explicitly
documented benchmark environment.

## 7. Current audit disposition

This document defines the audit scope and acceptance criteria.
It is not a completed audit certificate.

The final disposition must be based on the actual repository
revision, executed commands and retained evidence artifacts.

No unexecuted check is represented as PASS.
