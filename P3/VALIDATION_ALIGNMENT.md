P3 — Validation Alignment

1. Purpose

This document defines the validation contract for P3.

The implementation, tests, benchmark evidence, integrity inventory, CI result, and acceptance decision must refer to the same source commit.

A successful command, an existing report, or a historical CI run is not sufficient evidence for acceptance of a later commit.

No result may be described as PASS unless the corresponding command completed successfully and its output is retained or linked.

2. Repository and source of truth

- Repository: "adrianroman1/QFLPN-Quantum-Petri-Nets"
- Primary branch: "main"
- Java release: 21
- Python CI version: 3.12
- Benchmark CSV schema: "qflpn-benchmark-v2"
- Canonical CSV: "P3/benchmarks/benchmark_results_v2.csv"

The commit SHA used for a validation must be taken from the GitHub Actions run itself ("github.sha"). Do not copy an old SHA into this document as the current validated revision.

The CI workflow checks out the exact triggering commit. It does not push generated benchmark evidence back to "main". Evidence is uploaded as a workflow artifact and remains associated with that workflow run.

3. Validation layers

3.1 Java build and tests

The workflow executes:

mvn -B -f pom.xml validate
mvn -B -f pom.xml clean test

mvn -B -f P3/pom.xml validate
mvn -B -f P3/pom.xml clean test

The root project and P3 project are separate Maven builds. Both must pass.

3.2 Python tests

The workflow executes:

python -m pytest -q \
  P3/results/test_validate_benchmark.py \
  P3/tests/test_generate_integrity.py \
  P3/tests/test_verify_integrity.py

These tests cover the benchmark CSV validator and the integrity generator/verifier.

3.3 Benchmark execution

The CI benchmark is configured with:

Parameter| CI value
Dimension| 1,000,000
Warm-up iterations| 5
Measured iterations| 10
Threshold| 4,096
Parallelism| 2

The benchmark is executed through:

bash P3/results/run_benchmark.sh

The runner must:

- execute the P3 Maven tests before benchmarking;
- produce exactly one new V2 CSV record for the current run;
- validate the CSV using the configured parameters;
- create JSON, Markdown, and text reports;
- retain the run identifier in the generated evidence.

The benchmark is not accepted solely because it completes. Its numerical errors and CSV contract must also pass validation.

3.4 CSV validation

The canonical schema contains 28 columns.

The validator must reject:

- a missing or reordered header;
- missing or extra fields;
- invalid or non-finite numeric values;
- invalid configuration values;
- inconsistent speedup or throughput;
- numerical errors above the configured tolerance;
- duplicate run identifiers;
- missing benchmark records.

The workflow validates the generated CSV again with the expected CI configuration.

3.5 Report consistency

"P3/results/generate_benchmark_summary.py" matches the JSON validation report to exactly one CSV record using "run_id".

The summary must not combine the JSON report of one run with the CSV record of another run.

A missing report, a non-PASS report, a mismatched run ID, or inconsistent key measurements is a failure.

3.6 Integrity

Generate the deterministic manifest and checksum inventory:

python P3/tools/generate_integrity.py --write --root P3

Check reproducibility:

python P3/tools/generate_integrity.py --check --root P3

Verify independently:

python P3/tools/verify_integrity.py --root P3

The manifest and checksum inventory must:

- use deterministic sorted paths;
- reject duplicate or unsafe paths;
- exclude generated manifest/checksum files from the source inventory;
- exclude build/cache directories and symbolic links;
- include the manifest's own SHA-256 digest in the checksum file;
- detect missing, added, modified, or unlisted files.

"SHA256SUMS.txt" does not hash itself. This avoids a self-referential checksum.

4. CI acceptance gates

All gates are mandatory.

Gate| Required evidence
Root Maven validation| Successful workflow step
Root Maven tests| Successful workflow step and Surefire reports
P3 Maven validation| Successful workflow step
P3 Maven tests| Successful workflow step and Surefire reports
Python tests| Successful pytest exit code
Python syntax| Successful "py_compile" step
Benchmark| Successful run for the configured parameters
CSV validation| PASS for the V2 schema and expected configuration
JSON/CSV consistency| Matching run ID and matching measurements
Manifest generation| Successful generator execution
Manifest reproducibility| Successful "--check" execution
Independent SHA-256| Successful verifier execution
Evidence retention| Workflow artifacts uploaded

A skipped step is NOT RUN, not PASS.

A missing artifact is NOT VERIFIED, not PASS.

A historical successful run does not validate a newer commit.

5. Evidence identity

For every candidate acceptance, record:

- repository and branch;
- full commit SHA;
- workflow run ID and URL;
- workflow conclusion;
- Java and Python versions;
- Maven test totals and failures;
- pytest totals and failures;
- benchmark run ID and configuration;
- CSV validation result;
- integrity verification result;
- artifact names and links.

All evidence must originate from the same workflow run and triggering commit.

6. Current audit baseline

The Git audit preceding this Lot 5 delivery inspected "main" at:

"00f403da7adbcfe46a79b831809d4e9f6825723e"

At that audit:

- the CI workflow existed;
- the benchmark summary generator was missing;
- the acceptance report was missing;
- the validation alignment document contained historical status information;
- the workflow included an automatic evidence-commit job.

This baseline is an audit reference, not proof that the delivered Lot 5 files have passed CI.

The new workflow and reporting files must be committed before a new workflow run can validate them.

7. Acceptance rule

P3 may be marked ACCEPTED only when:

1. every mandatory CI gate passes;
2. all evidence belongs to the same commit;
3. benchmark CSV and JSON evidence agree;
4. independent integrity verification passes;
5. the acceptance report contains traceable run and artifact references.

Until then, the official status is:

PENDING VALIDATION — NOT ACCEPTED.
