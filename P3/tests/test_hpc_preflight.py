#!/usr/bin/env python3
"""Tests for the QFLPN P3 Slurm HPC preflight script.

These tests validate the preflight's source-level contract and its
relationship with the canonical target configuration and inventory
collector.

They do not simulate a real Slurm cluster and do not claim that the
preflight has run on 16 physical compute nodes.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PREFLIGHT = ROOT / "P3" / "hpc" / "slurm" / "p3-hpc-preflight.sbatch"
TARGET = ROOT / "P3" / "hpc" / "config" / "hpc-target.json"
COLLECTOR = ROOT / "P3" / "hpc" / "tools" / "collect_hpc_inventory.py"


class HpcPreflightContractTests(unittest.TestCase):
    """Verify the preflight's static integration contract."""

    @classmethod
    def setUpClass(cls) -> None:
        for path in (PREFLIGHT, TARGET, COLLECTOR):
            if not path.is_file():
                raise FileNotFoundError(
                    f"Required project file is missing: {path}"
                )

        cls.script = PREFLIGHT.read_text(encoding="utf-8")
        cls.target = json.loads(TARGET.read_text(encoding="utf-8"))
        cls.collector = COLLECTOR.read_text(encoding="utf-8")

    def test_script_has_bash_shebang_and_strict_mode(self) -> None:
        self.assertTrue(self.script.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -Eeuo pipefail", self.script)

    def test_script_uses_canonical_target_path(self) -> None:
        self.assertIn("P3/hpc/config/hpc-target.json", self.script)
        self.assertIn(
            'readonly CONFIG="${REPOSITORY_ROOT}/P3/hpc/config/hpc-target.json"',
            self.script,
        )

    def test_script_does_not_reference_obsolete_target_file(self) -> None:
        self.assertNotIn("hpc-664.json", self.script)

    def test_script_uses_v2_target_schema(self) -> None:
        self.assertIn(
            'readonly TARGET_SCHEMA="qflpn-p3-hpc-target-v2"',
            self.script,
        )
        self.assertEqual(
            self.target.get("schema"),
            "qflpn-p3-hpc-target-v2",
        )

    def test_target_is_explicitly_proposed_not_execution_evidence(self) -> None:
        self.assertEqual(
            self.target.get("status"),
            "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE",
        )
        self.assertIn(
            "PROPOSED_REFERENCE_CONFIGURATION_NOT_EVIDENCE",
            self.script,
        )

    def test_hardware_fields_are_read_from_nested_hardware_target(self) -> None:
        self.assertIsInstance(self.target.get("hardware_target"), dict)
        self.assertIn('hardware = target.get("hardware_target")', self.script)
        self.assertIn('hardware.get("node_groups")', self.script)
        self.assertIn('hardware["compute_nodes"]', self.script)
        self.assertIn('hardware["physical_cores_total"]', self.script)
        self.assertIn('hardware["ram_gib_total"]', self.script)
        self.assertIn('hardware["ram_gib_per_node"]', self.script)

    def test_reference_topology_is_16_nodes_and_664_physical_cores(self) -> None:
        hardware = self.target["hardware_target"]
        groups = hardware["node_groups"]

        nodes = sum(group["nodes"] for group in groups)
        cores = sum(
            group["nodes"] * group["physical_cores_per_node"]
            for group in groups
        )

        self.assertEqual(nodes, 16)
        self.assertEqual(cores, 664)
        self.assertEqual(hardware["compute_nodes"], 16)
        self.assertEqual(hardware["physical_cores_total"], 664)
        self.assertIn("EXPECTED_NODES=16", self.script)
        self.assertIn("EXPECTED_TASKS=664", self.script)

    def test_reference_ram_configuration_is_consistent(self) -> None:
        hardware = self.target["hardware_target"]

        self.assertEqual(hardware["ram_gib_per_node"], 256)
        self.assertEqual(hardware["ram_gib_total"], 4096)
        self.assertEqual(
            hardware["compute_nodes"] * hardware["ram_gib_per_node"],
            hardware["ram_gib_total"],
        )
        self.assertIn("ram_per_node != 256 or ram_total != 4096", self.script)

    def test_motherboard_contract_is_checked(self) -> None:
        motherboard = self.target["hardware_target"]["motherboard"]

        self.assertIs(motherboard["collection_required"], True)
        self.assertEqual(
            motherboard["fields"],
            ["manufacturer", "model", "version"],
        )
        self.assertEqual(motherboard["missing_value"], "UNAVAILABLE")

        self.assertIn('hardware.get("motherboard")', self.script)
        self.assertIn('"manufacturer", "model", "version"', self.script)
        self.assertIn('"UNAVAILABLE"', self.script)

    def test_spmv_proposal_preserves_664_workers(self) -> None:
        benchmark = self.target["benchmark"]

        self.assertEqual(benchmark["workload"], "SpMV")
        self.assertEqual(benchmark["parallelism_target"], 664)
        self.assertIn(664, benchmark["worker_counts"])

        self.assertIn('benchmark.get("workload") != "SpMV"', self.script)
        self.assertIn(
            'benchmark.get("parallelism_target") != 664',
            self.script,
        )
        self.assertIn("664 not in benchmark.get", self.script)

    def test_spmv_proposal_preserves_10_million_dimension(self) -> None:
        benchmark = self.target["benchmark"]

        self.assertEqual(
            benchmark["maximum_target_dimension"],
            10_000_000,
        )
        self.assertIn(10_000_000, benchmark["thresholds"])
        self.assertIn(
            'benchmark.get("maximum_target_dimension") != 10000000',
            self.script,
        )
        self.assertIn("10000000 not in benchmark.get", self.script)

    def test_benchmark_protocol_is_not_silently_changed(self) -> None:
        benchmark = self.target["benchmark"]

        self.assertEqual(benchmark["minimum_warmup"], 5)
        self.assertEqual(benchmark["minimum_valid_measurements"], 30)
        self.assertIn('benchmark.get("minimum_warmup") != 5', self.script)
        self.assertIn(
            'benchmark.get("minimum_valid_measurements") != 30',
            self.script,
        )

    def test_benchmark_execution_status_remains_not_executed(self) -> None:
        self.assertEqual(
            self.target["benchmark"]["execution_status"],
            "NOT_EXECUTED",
        )
        self.assertIn(
            'benchmark.get("execution_status") != "NOT_EXECUTED"',
            self.script,
        )
        self.assertIn(
            '"benchmark_execution_status": "NOT_EXECUTED"',
            self.script,
        )

    def test_script_checks_slurm_allocation_size(self) -> None:
        self.assertIn('"${SLURM_NNODES}"', self.script)
        self.assertIn('"${SLURM_NTASKS}"', self.script)
        self.assertIn('scontrol show job "$SLURM_JOB_ID"', self.script)
        self.assertIn(
            'scontrol show hostnames "$SLURM_JOB_NODELIST"',
            self.script,
        )

    def test_inventory_collection_uses_one_task_per_node(self) -> None:
        self.assertRegex(
            self.script,
            re.compile(r"--nodes=\"\$EXPECTED_NODES\""),
        )
        self.assertRegex(
            self.script,
            re.compile(r"--ntasks=\"\$EXPECTED_NODES\""),
        )
        self.assertIn("--ntasks-per-node=1", self.script)

    def test_inventory_collection_uses_canonical_collector_command(self) -> None:
        self.assertIn(
            'python3 "$P3_HPC_COLLECTOR" collect',
            self.script,
        )
        self.assertIn(
            'python3 "$COLLECTOR" validate "$CONFIG" "${INVENTORY_FILES[@]}"',
            self.script,
        )
        self.assertIn('subparsers.add_parser("collect"', self.collector)
        self.assertIn(
            'subparsers.add_parser(\n        "validate"',
            self.collector,
        )

    def test_inventory_schema_matches_collector(self) -> None:
        self.assertIn(
            'readonly INVENTORY_SCHEMA="qflpn-p3-hpc-node-inventory-v1"',
            self.script,
        )
        self.assertIn(
            'NODE_SCHEMA = "qflpn-p3-hpc-node-inventory-v1"',
            self.collector,
        )

    def test_inventory_provenance_checks_job_and_process_identity(self) -> None:
        self.assertIn('"SLURM_JOB_ID"', self.script)
        self.assertIn('"SLURM_PROCID"', self.script)
        self.assertIn("SLURM_JOB_ID_CONSISTENCY=PASS", self.script)
        self.assertIn("SLURM_PROCID_COVERAGE=PASS", self.script)

    def test_duplicate_hostnames_are_rejected(self) -> None:
        self.assertIn("len(set(hostnames)) != expected_count", self.script)
        self.assertIn("duplicate inventory hostnames", self.script.lower())

    def test_collector_deferred_status_is_not_misreported_as_pass(self) -> None:
        self.assertIn(
            'overall not in {"PASS", "DEFERRED", "FAIL"}',
            self.script,
        )
        self.assertIn('if overall == "FAIL":', self.script)
        self.assertIn('"PREFLIGHT_DEFERRED"', self.script)
        self.assertIn('"validation_status": overall', self.script)

    def test_collector_exit_code_is_checked_against_json_verdict(self) -> None:
        self.assertIn(
            'EXPECTED_VALIDATION_EXIT_CLASS="PASS"',
            self.script,
        )
        self.assertIn(
            'EXPECTED_VALIDATION_EXIT_CLASS="DEFERRED_OR_FAIL"',
            self.script,
        )
        self.assertIn(
            'if exit_code != 0 or overall != "PASS":',
            self.script,
        )
        self.assertIn(
            'if exit_code != 1:',
            self.script,
        )
        self.assertIn(
            'if overall == "DEFERRED":',
            self.script,
        )
        self.assertIn(
            'elif overall == "FAIL":',
            self.script,
        )
        self.assertIn(
            "COLLECTOR_EXIT_STATUS_CONSISTENCY=PASS",
            self.script,
        )

    def test_deferred_collector_exit_code_is_not_execution_failure(self) -> None:
        self.assertIn(
            '1)\n        EXPECTED_VALIDATION_EXIT_CLASS="DEFERRED_OR_FAIL"',
            self.script,
        )
        self.assertIn('overall == "DEFERRED"', self.script)
        self.assertIn('"PREFLIGHT_DEFERRED"', self.script)

    def test_unexpected_collector_exit_codes_are_rejected(self) -> None:
        self.assertIn(
            '*)\n        cat "${OUTPUT_DIR}/HPC_TARGET_VALIDATION.json" >&2',
            self.script,
        )
        self.assertIn(
            "Validatorul colectorului a returnat un cod neașteptat",
            self.script,
        )

    def test_fail_verdict_still_fails_preflight(self) -> None:
        self.assertIn('if overall == "FAIL":', self.script)
        self.assertIn("raise SystemExit(3)", self.script)

    def test_summary_distinguishes_preflight_from_cluster_acceptance(self) -> None:
        self.assertIn(
            '"cluster_acceptance": "NOT_EVALUATED"',
            self.script,
        )
        self.assertIn(
            '"p3_verdict": "NOT_EVALUATED"',
            self.script,
        )
        self.assertIn('"P3_ACCEPTED"', self.script)

        # The marker is explanatory only; this script must never issue it
        # as an acceptance verdict.
        self.assertIn(
            "'P3_ACCEPTED' is not declared by the preflight",
            self.script,
        )

    def test_script_does_not_claim_to_execute_spmv(self) -> None:
        self.assertIn("does NOT:", self.script)
        self.assertIn("execute SpMV", self.script)
        self.assertIn("BENCHMARK_EXECUTION_STATUS=NOT_EXECUTED", self.script)

    def test_final_evidence_gate_remains_p3_validation(self) -> None:
        self.assertIn("p3_validation", self.script)
        self.assertIn(
            "Dovezile benchmarkului trebuie validate separat prin p3_validation.",
            self.script,
        )

    def test_preflight_does_not_modify_workflow_or_integrity_files(self) -> None:
        forbidden_paths = (
            ".github/workflows/p3-validation.yml",
            "P3/MANIFEST.txt",
            "P3/SHA256SUMS.txt",
        )

        for path in forbidden_paths:
            self.assertNotIn(path, self.script)


if __name__ == "__main__":
    unittest.main()
