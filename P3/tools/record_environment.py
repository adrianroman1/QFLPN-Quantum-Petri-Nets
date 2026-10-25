#!/usr/bin/env python3
"""Capture and validate the actual environment used by a QFLPN P3 run."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def run_command(command: list[str], *, required: bool = False) -> str:
    """Return command output without inventing a value when unavailable."""
    executable = shutil.which(command[0])
    if executable is None:
        if required:
            raise RuntimeError(f"Required executable is unavailable: {command[0]}")
        return "UNAVAILABLE"

    try:
        result = subprocess.run(
            [executable, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if required:
            raise RuntimeError(
                f"Cannot execute required command {command[0]}: {exc}"
            ) from exc
        return f"UNAVAILABLE: {type(exc).__name__}: {exc}"

    output = "\n".join(
        part.strip()
        for part in (result.stdout, result.stderr)
        if part.strip()
    ).strip()

    if result.returncode != 0:
        if required:
            raise RuntimeError(
                f"Required command failed ({command[0]}): {output}"
            )
        return f"UNAVAILABLE: exit={result.returncode}; {output}"

    return output or "NO_OUTPUT"


def git_value(root: Path, *arguments: str) -> str:
    """Read repository metadata from Git; fail if the checkout is invalid."""
    return run_command(
        ["git", "-C", str(root), *arguments],
        required=True,
    )


def positive_integer(value: str | None, name: str) -> int:
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def capture_environment(
    root: Path,
    *,
    run_id: str,
    dimension: int,
    warmup_iterations: int,
    measured_iterations: int,
    threshold: int,
    parallelism: int,
) -> dict[str, Any]:
    """Capture actual host, runtime, repository and benchmark configuration."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Repository root does not exist: {root}")
    if not run_id or run_id.strip() != run_id:
        raise ValueError("RUN_ID must be non-empty and canonical")

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    cpu_count = os.cpu_count()
    if cpu_count is None or cpu_count <= 0:
        raise RuntimeError("Python could not determine the logical CPU count")

    try:
        loadavg = os.getloadavg()
        load_average: list[float] | None = [float(x) for x in loadavg]
    except (AttributeError, OSError):
        load_average = None

    memory: dict[str, int | None] = {
        "total_bytes": None,
        "available_bytes": None,
    }
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="ascii").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].rstrip(":") in {
                "MemTotal",
                "MemAvailable",
            }:
                values[parts[0].rstrip(":")] = int(parts[1]) * 1024
        memory["total_bytes"] = values.get("MemTotal")
        memory["available_bytes"] = values.get("MemAvailable")

    data: dict[str, Any] = {
        "schema": "qflpn-p3-environment-v1",
        "captured_at_utc": timestamp,
        "run_id": run_id,
        "repository": {
            "root": str(root),
            "remote_origin": git_value(root, "remote", "get-url", "origin"),
            "branch": os.environ.get("GITHUB_REF_NAME", "UNAVAILABLE"),
            "commit": git_value(root, "rev-parse", "HEAD"),
            "commit_dirty": bool(
                git_value(root, "status", "--porcelain").strip()
            ),
        },
        "runner": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "UNAVAILABLE",
            "logical_cpu_count": cpu_count,
            "load_average_1_5_15": load_average,
            "memory": memory,
            "github_runner_os": os.environ.get(
                "RUNNER_OS", "UNAVAILABLE"
            ),
            "github_runner_arch": os.environ.get(
                "RUNNER_ARCH", "UNAVAILABLE"
            ),
            "github_workflow": os.environ.get(
                "GITHUB_WORKFLOW", "UNAVAILABLE"
            ),
            "github_run_id": os.environ.get(
                "GITHUB_RUN_ID", "UNAVAILABLE"
            ),
            "github_run_attempt": os.environ.get(
                "GITHUB_RUN_ATTEMPT", "UNAVAILABLE"
            ),
        },
        "runtime": {
            "python": sys.version.replace("\n", " "),
            "java": run_command(["java", "-version"], required=True),
            "maven": run_command(["mvn", "--version"], required=True),
            "git": run_command(["git", "--version"], required=True),
        },
        "benchmark": {
            "dimension": dimension,
            "warmup_iterations": warmup_iterations,
            "measured_iterations": measured_iterations,
            "threshold": threshold,
            "parallelism": parallelism,
        },
    }

    validate_environment(data)
    return data


def validate_environment(data: dict[str, Any]) -> None:
    """Fail closed when required provenance fields are absent or invalid."""
    if data.get("schema") != "qflpn-p3-environment-v1":
        raise ValueError("Unsupported environment schema")

    if not data.get("run_id"):
        raise ValueError("Environment RUN_ID is missing")

    repository = data.get("repository")
    runner = data.get("runner")
    runtime = data.get("runtime")
    benchmark = data.get("benchmark")

    if not all(isinstance(item, dict) for item in (
        repository, runner, runtime, benchmark
    )):
        raise ValueError("Environment sections must be JSON objects")

    for key in ("commit", "remote_origin"):
        value = repository.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing repository field: {key}")

    for key in ("os", "machine", "logical_cpu_count"):
        if runner.get(key) in (None, "", "UNAVAILABLE"):
            raise ValueError(f"Missing runner field: {key}")

    for key in ("python", "java", "maven", "git"):
        value = runtime.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing runtime field: {key}")
        if value.startswith("UNAVAILABLE"):
            raise ValueError(f"Runtime command unavailable: {key}")

    for key in (
        "dimension",
        "warmup_iterations",
        "measured_iterations",
        "threshold",
        "parallelism",
    ):
        value = benchmark.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"Invalid benchmark environment field: {key}")


def render_text(data: dict[str, Any]) -> str:
    """Render a human-readable report from the validated JSON object."""
    validate_environment(data)

    lines = [
        "QFLPN P3 EXECUTION ENVIRONMENT",
        f"Captured UTC: {data['captured_at_utc']}",
        f"RUN_ID: {data['run_id']}",
        "",
        "REPOSITORY",
        f"Root: {data['repository']['root']}",
        f"Origin: {data['repository']['remote_origin']}",
        f"Branch: {data['repository']['branch']}",
        f"Commit: {data['repository']['commit']}",
        f"Working tree dirty at capture: {data['repository']['commit_dirty']}",
        "",
        "RUNNER",
    ]

    for key, value in data["runner"].items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")

    lines.extend(["", "RUNTIME"])
    for key, value in data["runtime"].items():
        lines.append(f"{key}:")
        lines.extend(f"  {line}" for line in str(value).splitlines())

    lines.extend(["", "BENCHMARK CONFIGURATION"])
    for key, value in data["benchmark"].items():
        lines.append(f"{key}: {value}")

    return "\n".join(lines) + "\n"


def atomic_write(path: Path, content: str) -> None:
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"Refusing to overwrite symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture and validate the actual P3 execution environment."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    parser.add_argument("--dimension", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--threshold", type=int, default=None)
    parser.add_argument("--parallelism", type=int, default=None)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("P3/reports/environment.json"),
    )
    parser.add_argument(
        "--text-output",
        type=Path,
        default=Path("P3/reports/environment.txt"),
    )
    args = parser.parse_args()

    try:
        run_id = args.run_id
        if not run_id:
            raise ValueError("--run-id or RUN_ID is required")

        def config(cli_value: int | None, env_name: str) -> int:
            if cli_value is not None:
                if cli_value <= 0:
                    raise ValueError(f"{env_name} must be positive")
                return cli_value
            return positive_integer(os.environ.get(env_name), env_name)

        data = capture_environment(
            args.root,
            run_id=run_id,
            dimension=config(args.dimension, "N"),
            warmup_iterations=config(args.warmup, "WARMUP"),
            measured_iterations=config(args.iterations, "ITERATIONS"),
            threshold=config(args.threshold, "THRESHOLD"),
            parallelism=config(args.parallelism, "PARALLELISM"),
        )

        json_content = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
        text_content = render_text(data)

        atomic_write(args.json_output, json_content)
        atomic_write(args.text_output, text_content)

        print("P3_ENVIRONMENT_CAPTURE: PASS")
        print(f"P3_ENVIRONMENT_RUN_ID={run_id}")
        print(f"P3_ENVIRONMENT_JSON={args.json_output}")
        print(f"P3_ENVIRONMENT_TEXT={args.text_output}")
        return 0

    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print(
            f"P3_ENVIRONMENT_CAPTURE: FAIL: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
