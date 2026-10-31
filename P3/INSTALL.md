# P3 parallel – wave 2 (repairs the errors of wave 1)

Base commit: `4cb7634` (main, 2026-10-29). Hashes in `BASE_HASHES.txt`.

## What went wrong with wave 1, and what changed

Wave 1 asked you to edit `SparseMatrixCSR.java` (three zero-copy accessors). That
file kept evolving, the edit was not applied, and the new strategy classes no
longer compiled (4 errors: `rowPointersView()`, `valuesView()`,
`columnIndicesView()`). **Wave 2 does not touch any of your files except the
workflow, additively.** The strategies now use only public APIs.

## Contents

| Folder | What it is | How to install |
|---|---|---|
| `ADD/` | 10 new files | `cp -rn ADD/P3 ./` (never overwrites) |
| `REPLACE_MY_UPLOADED_FILES/` | 9 files from wave 1 that are already on main, improved | copy over the existing ones (check `BASE_HASHES.txt` first) |
| `PATCHES/01-…patch` | Additive workflow change (+49 lines) | `git apply --3way PATCHES/01-p3-validation-harness-gate.patch` |
| `EXAMPLE_ONLY_DO_NOT_COMMIT/` | One run from a 1-CPU sandbox | do **not** commit; shows the formats |

```bash
git rev-parse HEAD                       # expect 4cb7634 (or compare BASE_HASHES.txt)
cp -rn ADD/P3 ./
cp -r  REPLACE_MY_UPLOADED_FILES/P3 ./   # only if your 9 files match BASE_HASHES.txt
git apply --3way PATCHES/01-p3-validation-harness-gate.patch

mvn -f P3/pom.xml test                   # Java: 508 tests expected
python -m pytest P3/tests P3/results     # Python: 348 tests expected
bash P3/results/run_parallel_harness.sh  # one command, on the multi-core machine
```

Nothing is deleted. `MANIFEST.txt` and `SHA256SUMS.txt` are untouched; the
workflow regenerates and verifies them in its own run.

## Defects from the external audit, one by one

| ID | Claim | Verdict | Fix |
|---|---|---|---|
| D01 | `javac … \| grep … \|\| true` can hide a compile error | **True**, in `run_parallel_harness.sh` | Real exit status kept, `build.log`, `BUILD_FAILED.txt`, exit 1; test with a deliberately broken source |
| D02 | C1 can be PASS with no observations | **True** for `evaluate()` itself (the normal path exited earlier); completeness was never checked | C0 and C8 added, C1 fails on empty data, exit status 2 on invalid input, `--strict` |
| D03 | Not integrated in `p3_validation` | **True** (deliberately not wired in wave 1) | Additive blocking step + `check_harness_gate.py` (see below) |
| D04 | No MPI / distributed computing | **True** | Distribution plan and in-process simulation are delivered and tested; the MPI binding is **not** implemented |
| D05 | Threshold barely explored | **True** | `THRESHOLDS` sweep, reported as `FJ_PLAN_T<threshold>`; `THRESHOLD_MODE` explicit |
| D06 | Scaling beyond 1/2/4 | Partly | `PARALLELISMS` accepts any list; values above the visible cores are skipped and recorded; the 664-core target is validated by inventories, not by worker counts |

## The workflow step

Placed before “Persist V2 reports…”, writing to
`P3/results/raw/<RUN_ID>/harness-smoke/`. Existing steps already upload that
tree, list it in the summary index, include it in the global manifest and commit
it, so `.sh`, `.csv`, `.txt`, `.md`, `MANIFEST.txt` and `SHA256SUMS.txt` appear
automatically. It blocks on: build failure, C0, C1, C2, C7, C8 and the run's own
SHA-256 inventory. C3–C6 only warn (shared runners are noisy). It is not part of
`ci-outcomes.json`, whose stage schema stays unchanged.

**Not executed in GitHub Actions** (no access from here). Verified instead: the
YAML parses, the step's bash was run locally on a copy of the repository, and the
repository's own `compute_checksums.py` and
`verify_final_package.verify_global_integrity` accept the resulting tree.

## Untested

- `P3/hpc/slurm/p3-hpc-intranode.sbatch`: syntax-checked only; no Slurm available.
- MPI: nothing was written or run.
