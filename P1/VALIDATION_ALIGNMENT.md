# P1 implementation alignment with the 2026-10-18 preprint

This note records the implementation corrections prepared against the Dropbox
source `P1_QFLPN_BIBLIOGRAPHY_FINAL.tex` last modified 2026-10-18 11:04 UTC.
The preprint is authoritative. Git code is implementation material only.

## Scope and invariants

- The four-qubit reference uses lexicographic computational-basis order
  `|0000>` through `|1111>`, dimension 16, and double precision.
- The activation map is `theta = 2 asin(sqrt(lambda))`.
- The rotation matrix uses `cos(theta/2)` and `sin(theta/2)`.
- The declared controlled reference gate is
  `C^3X = (I_8 - P_c) tensor I_2 + P_c tensor X`, with
  `P_c = |111><111|` on the first three qubits.
- Density-matrix validation includes trace, Hermiticity, and
  `epsilon_PSD = max(0, -lambda_min(rho))`.

## File-level corrections

### `P1/code/qflpn_reference.py`

Added a square-matrix/Hermiticity-checked PSD residual implementation. The
existing fuzzy-to-angle mapping and state preparation already matched the
preprint and were retained.

### `P1/code/qflpn_transition_operator.py`

Added the explicit projector-form `c3x()` operator. The four-qubit P1 reference
transition now defaults to `C^3X @ U_local`; the generic single-control `CX`
constructor remains available when both control and target are supplied.
The operator basis ordering is MSB-first/lexicographic, matching the preprint.

### `P1/tests/qflpn_validation.py`

Made the sibling `P1/code` import deterministic; added PSD, C^3X basis-action,
unitarity, involution, and global-transition checks. Numerical failures now
raise a non-zero process exit instead of merely printing a review message.
The self-fidelity check remains only a sanity check, not independent evidence.

### `P1/tests/qflpn_operator_validation.py`

Changed both CSR block construction and its analytic comparator to the
half-angle convention. Added input checks for positive even dimensions and
`mu` in `[0,1]`; numerical failures now stop the run. This script is retained
as a helper only: the preprint at §8 explicitly assigns CSR/sparse evolution
as a separate computational study in P3, so its timings are not P1 results.

### `.github/workflows/p1-validation.yml`

Added a dedicated CI workflow to compile P1 Python files and run both P1
validation scripts with NumPy/SciPy installed. This avoids conflating the
existing Java/Maven CI with P1 Python validation.

## Explicitly unchanged

- No `.tex` or `.pdf` preprint file was modified.
- No bibliography entry, citation, or reference was modified.
- No P2, P3, P4, root-level shared Python, or shared MATLAB file was modified.
- No existing file was deleted or moved.

## Verification boundary

The CSR helper is not used as evidence for P1's formal or empirical claims.
The P1 four-qubit validation establishes only the declared finite-dimensional
reference construction and its numerical invariants. CI timing thresholds are
reported separately from numerical correctness.
