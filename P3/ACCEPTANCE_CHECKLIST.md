# P3 — Final Acceptance Checklist

## 1. Acceptance policy

P3 may be marked accepted only when all mandatory
mathematical, software, benchmark, reproducibility,
integrity, and CI requirements pass.

A successful root project build does not prove that
P3 is accepted.

A successful workflow configuration does not prove
that the workflow executed successfully.

A skipped stage is not a passing stage.

All final evidence must refer to the same accepted
commit.

## 2. Repository provenance

- [ ] Repository and branch recorded.
- [ ] Final commit SHA recorded.
- [ ] GitHub Actions workflow run recorded.
- [ ] Workflow run corresponds to the final commit.
- [ ] Environment metadata preserved.
- [ ] Run identifier recorded.

## 3. CSR correctness

- [ ] CSR dimensions validated.
- [ ] Row pointer length validated.
- [ ] Row pointer monotonicity validated.
- [ ] First row pointer equals zero.
- [ ] Final row pointer equals the number of stored entries.
- [ ] Column indices are within matrix bounds.
- [ ] Values and column index arrays have equal lengths.
- [ ] Empty rows are supported.
- [ ] Duplicate columns have documented semantics.
- [ ] `get()` follows duplicate-column semantics.
- [ ] Sequential SpMV follows the same semantics.
- [ ] Invalid CSR structures are rejected.
- [ ] Zero-sized dimensions are tested where supported.

## 4. Independent mathematical validation

- [ ] Dense oracle implemented independently.
- [ ] Dense oracle does not call CSR multiplication.
- [ ] Reference fixture produces the expected output.
- [ ] More-rows-than-columns matrix tested.
- [ ] More-columns-than-rows matrix tested.
- [ ] Empty rows tested.
- [ ] Duplicate columns tested.
- [ ] Single-row matrix tested.
- [ ] Single-column matrix tested.
- [ ] Deterministic generated matrices tested.
- [ ] Numeric tolerance documented.
- [ ] Numeric comparisons pass.

Required tolerance:

```text
1e-12
