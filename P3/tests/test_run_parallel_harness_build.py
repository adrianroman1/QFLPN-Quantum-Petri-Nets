#!/usr/bin/env python3
"""The harness runner must fail closed when the Java build fails (D01)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "P3" / "results" / "run_parallel_harness.sh"
HARNESS_JAVA = ROOT / "P3" / "benchmarks" / "harness" / "ParallelSpmvHarness.java"

needs_tools = pytest.mark.skipif(
    shutil.which("javac") is None or shutil.which("bash") is None,
    reason="javac and bash are required",
)


def make_tree(tmp_path: Path) -> tuple[Path, Path]:
    tree = tmp_path / "tree"
    (tree / "P3" / "results").mkdir(parents=True)
    (tree / "P3" / "benchmarks" / "harness").mkdir(parents=True)
    shutil.copy(SCRIPT, tree / "P3" / "results" / SCRIPT.name)
    shutil.copy(HARNESS_JAVA,
                tree / "P3" / "benchmarks" / "harness" / HARNESS_JAVA.name)
    src = tmp_path / "src"
    src.mkdir()
    return tree, src


def run_script(tree: Path, src: Path, run_id: str):
    env = dict(os.environ, P3_SRC_DIR=str(src), RUN_ID=run_id,
               SIZES="1000", FORKS="1", WARMUP="1", ITERATIONS="1")
    return subprocess.run(
        ["bash", str(tree / "P3" / "results" / SCRIPT.name)],
        env=env, capture_output=True, text=True, timeout=240)


def test_script_does_not_swallow_the_compiler_status() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    compile_block = text.split("[1/8] compile")[1].split("run_java()")[0]

    assert "|| true" not in compile_block
    assert "grep -v" not in compile_block
    assert "BUILD_FAILED" in compile_block
    assert "build.log" in compile_block


@needs_tools
def test_a_java_compile_error_stops_the_run_and_nothing_is_measured(
        tmp_path: Path) -> None:
    tree, src = make_tree(tmp_path)
    (src / "Broken.java").write_text(
        "package hpc.csr;\nclass Broken { int x = \"not an int\"; }\n",
        encoding="utf-8")

    result = run_script(tree, src, "build-failure-test")
    out = tree / "P3" / "results" / "harness" / "build-failure-test"

    assert result.returncode != 0
    assert "BUILD_FAILED" in result.stderr
    assert "P3_VALIDATION_FAILED" in result.stderr
    assert (out / "BUILD_FAILED.txt").is_file()
    assert "error" in (out / "build.log").read_text(encoding="utf-8")
    assert not (out / "harness_raw_iterations.csv").exists()
    assert not (out / "harness_verdict.json").exists()


@needs_tools
def test_a_missing_source_directory_also_fails(tmp_path: Path) -> None:
    tree, src = make_tree(tmp_path)           # no .java files in src

    result = run_script(tree, src, "no-sources-test")

    assert result.returncode != 0
    assert "BUILD_FAILED" in result.stderr
