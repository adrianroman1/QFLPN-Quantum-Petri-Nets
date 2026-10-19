# P2 Validation Alignment

## 1. Purpose

This document defines the relationship between the P2 implementation,
its automated tests, numerical checks and manuscript claims.

The purpose is to prevent a software test from being presented as
proof of a broader mathematical or physical statement.

## 2. Validation layers

### Layer A — Input validation

Checks:

- exactly four activation values are supplied;
- values are numeric;
- Boolean values are rejected;
- values are finite;
- each activation belongs to [0, 1].

Evidence:

- `tests/test_reference.py`
- `tests/test_adversarial.py`

Scope limitation:

Input validation establishes that the implementation rejects
specified invalid inputs. It does not establish the correctness
of the model's scientific assumptions.

### Layer B — Operator construction

Checks:

- four single-qubit rotations are constructed;
- tensor-product dimensions are 16 by 16;
- the C3X gate has the intended basis permutation;
- transition ordering is explicitly defined.

Evidence:

- `tests/test_transition_operator.py`
- `tests/test_ordering_sensitivity.py`

Canonical convention:

\[
U = C_{3X} U_{\mathrm{rot}}.
\]

The rightmost operator acts first.

The basis convention must be documented consistently wherever
the operator is used.

### Layer C — State-vector properties

Checks:

- state-vector dimension;
- finite amplitudes;
- normalization;
- norm preservation under a unitary transition.

Evidence:

- `tests/test_reference.py`
- `tests/test_transition_operator.py`
- `tests/test_adversarial.py`

Scope limitation:

These checks concern the implemented finite-dimensional state
representation. They do not demonstrate physical hardware behavior.

### Layer D — Density matrices

For a normalized pure state \(|\psi\rangle\), the implementation
constructs:

\[
\rho = |\psi\rangle\langle\psi|.
\]

Required properties:

\[
\rho^\dagger = \rho,
\]

\[
\operatorname{Tr}(\rho)=1,
\]

\[
\rho \succeq 0.
\]

For a pure state:

\[
\rho^2=\rho,
\qquad
\operatorname{Tr}(\rho^2)=1.
\]

Evidence:

- `tests/test_density_matrix.py`
- `tests/test_entanglement.py`

Numerical positivity must be assessed using a declared tolerance.

### Layer E — Independent simulator comparison

The PennyLane implementation is compared with the NumPy reference.

The comparison must be run, not merely imported or syntax-checked.

Required evidence:

- installed PennyLane version;
- actual simulator output;
- state fidelity;
- amplitude error;
- command exit code.

Evidence location:

- `code/run_qflpn_pennylane.py`
- `tests/test_pennylane_circuit.py`

A skipped simulator test remains unverified.

### Layer F — Integrity and reproducibility

Checks:

- deterministic manifest generation;
- SHA-256 verification;
- report syntax validation;
- CI execution.

Evidence:

- `tools/generate_manifest.py`
- `tools/verify_sha256.py`
- `tools/validate_reports.py`
- `.github/workflows/p2-validation.yml`

A direct-dependency pin file is not a complete transitive lock.

## 3. Manuscript alignment

Each mathematical statement in the P2 manuscript must be mapped
to one of the following:

1. formal derivation;
2. exact algebraic identity;
3. numerical experiment;
4. software implementation detail;
5. empirical benchmark.

The evidence type must not be substituted for another.

For example, a passing unitary-matrix test supports the numerical
unitarity of the tested matrix. It does not replace a proof that
the matrix construction satisfies the intended mathematical
definition for all admissible inputs.

## 4. Acceptance status

No validation layer is automatically accepted by the existence
of its source file.

Acceptance requires execution evidence associated with the exact
reviewed source revision.

## 5. Change control

Any change to:

- activation encoding;
- qubit ordering;
- gate ordering;
- basis convention;
- matrix construction;
- density-matrix calculation;

requires rerunning all affected tests and regenerating the
integrity manifest.
