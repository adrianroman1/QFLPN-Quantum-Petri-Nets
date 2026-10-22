# P3 — Manifest and SHA-256 integrity

## Purpose

P3 uses one generator as the authoritative source for:

- `P3/MANIFEST.txt`
- `P3/SHA256SUMS.txt`

Hash values must never be typed or edited manually.

## Generate the files

Run these commands from the repository root:

```bash
python3 P3/tools/generate_integrity.py --write
python3 P3/tools/generate_integrity.py --check
```

The `--write` operation regenerates both files.

The `--check` operation is read-only. It exits with a non-zero status
when either generated file is missing or does not match the current
P3 file tree.

## Inventory policy

The manifest inventories regular files below P3.

Paths are:

- relative to the P3 directory;
- represented with forward slashes;
- sorted deterministically.

The generator excludes:

- `.git`;
- Maven `target` directories;
- Python `__pycache__`;
- `.pytest_cache`;
- `.mypy_cache`;
- the two generated integrity files themselves.

Symbolic links are not followed or inventoried.

The checksum file includes the hash of `MANIFEST.txt`.

## Required maintenance procedure

After adding, deleting, or changing P3 files:

1. Run the generator with `--write`.
2. Review the generated manifest.
3. Review the generated checksum list.
4. Commit the changed source files and both generated outputs.
5. Require CI to pass `--check`.

Do not manually edit either generated output.

## Benchmark workflow

A manually dispatched P3 workflow runs the benchmark with:

- N = 1,000,000;
- warmup = 5;
- iterations = 10;
- threshold = 4096;
- parallelism = 2.

After the benchmark, the workflow regenerates both global integrity
files and verifies them again.

The workflow uploads the benchmark CSV, run-specific evidence,
manifest, and checksum list as an Actions artifact.

The workflow does not commit generated files back to the repository.
The artifact is evidence from that execution, not an automatic change
to the Git branch.
