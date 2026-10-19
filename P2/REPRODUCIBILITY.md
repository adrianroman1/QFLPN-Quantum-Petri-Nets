# P2 Reproducibility Contract

## 1. Scope

This document defines the reproducibility inputs, numerical conventions,
generated artifacts, and validation expectations for the QFLPN P2
four-qubit operator instance.

The canonical manuscript is:

`P2_QFLPN_BIBLIOGRAPHY_FINAL.pdf`

The reference configuration is:

`P2/reports/reference_config.json`

The canonical NumPy implementation is:

`P2/code/qflpn_reference.py`

## 2. Mathematical specification

The model uses four qubits and a sixteen-dimensional Hilbert space.

The initial state is:

\[
|0000\rangle.
\]

The activation vector is:

\[
\lambda=(0.85,0.90,0.45,0.70).
\]

Each activation is encoded by:

\[
\theta_i=2\arcsin\sqrt{\lambda_i}.
\]

The single-qubit operation is:

\[
RY(\theta_i).
\]

The rotation operator is:

\[
U_{\mathrm{rot}}=
RY(\theta_1)\otimes
RY(\theta_2)\otimes
RY(\theta_3)\otimes
RY(\theta_4).
\]

The controlled operation is C3X, with q1, q2, and q3 as controls
and q4 as target.

In the big-endian computational basis, C3X exchanges indices 14 and 15.

The complete operator is:

\[
U=C3X\,U_{\mathrm{rot}}.
\]

The final state is:

\[
|\psi\rangle=U|0000\rangle.
\]

The density matrix is:

\[
\rho=|\psi\rangle\langle\psi|.
\]

## 3. Basis convention

The computational basis is ordered as:

`|0000>, |0001>, ..., |1111>`.

The first qubit is the most-significant bit.

The fourth qubit is the least-significant bit.

All state-vector and matrix artifacts use this convention.

## 4. Numerical conventions

- Numerical representation: `complex128`.
- Probability convention: `abs(psi_i)**2`.
- Pure-state fidelity: squared overlap.
- Reduced partition: `(q1,q2,q3)|q4`.
- Von Neumann entropy: base-2 logarithm.
- Reference tolerance: `1e-12`.

## 5. Generate reference artifacts

From the repository root:

```bash
python P2/tools/generate_reference_artifacts.py \
  --config P2/reports/reference_config.json
