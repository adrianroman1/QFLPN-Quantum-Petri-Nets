#!/usr/bin/env python3
"""
P2-BENCH-CONFIG-01
Contract Integration Audit

Verifică:
- structura benchmark_config.json;
- API-ul BenchmarkContract;
- semnătura load_benchmark_contract;
- importul și utilizarea contractului în runner;
- integrarea contractului în validator;
- absența constantelor istorice pentru artefacte.

Nu modifică fișierele sursă.
Generează audit/contract_integration.json.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import sys

from datetime import datetime, timezone
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

BENCHMARK_DIR = ROOT / "P2" / "benchmarks"

CONFIG_PATH = BENCHMARK_DIR / "benchmark_config.json"

CONTRACT_PATH = BENCHMARK_DIR / "benchmark_contract.py"

RUNNER_PATH = BENCHMARK_DIR / "benchmark_runner.py"

VALIDATOR_PATH = BENCHMARK_DIR / "validate_benchmark.py"

REPORT_PATH = ROOT / "audit" / "contract_integration.json"


# =========================================================
# CONTRACT CONSTANTS
# =========================================================

ARTIFACT_KEYS = (
    "json",
    "csv",
    "markdown",
    "environment",
)

CONTRACT_PROPERTIES = (
    "output_directory",
    "json_path",
    "csv_path",
    "markdown_path",
    "environment_path",
)

CONTRACT_FIELDS = (
    "config_path",
    "p2_root",
    "config",
    "artifacts",
    "artifact_paths",
)

FORBIDDEN_CONSTANTS = {
    "JSON_FILENAME",
    "CSV_FILENAME",
    "MARKDOWN_FILENAME",
    "ENVIRONMENT_FILENAME",
}


# =========================================================
# GENERAL HELPERS
# =========================================================

def parse_python_file(
    path: Path,
) -> tuple[ast.Module | None, str | None]:

    if not path.is_file():
        return None, f"File does not exist: {path}"

    try:
        source = path.read_text(
            encoding="utf-8"
        )

        return ast.parse(
            source,
            filename=str(path),
        ), None

    except Exception as exc:

        return None, str(exc)


def top_level_functions(
    tree: ast.Module,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:

    return {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


def top_level_classes(
    tree: ast.Module,
) -> dict[str, ast.ClassDef]:

    return {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def imported_names(
    tree: ast.Module,
) -> set[str]:

    result = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.ImportFrom):

            for alias in node.names:

                result.add(
                    alias.asname or alias.name
                )

        elif isinstance(node, ast.Import):

            for alias in node.names:

                result.add(
                    alias.asname
                    or alias.name.split(".")[0]
                )

    return result


def calls_named(
    tree: ast.Module,
    function_name: str,
) -> list[ast.Call]:

    result = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        function = node.func

        if (
            isinstance(function, ast.Name)
            and function.id == function_name
        ):

            result.append(node)

        elif (
            isinstance(function, ast.Attribute)
            and function.attr == function_name
        ):

            result.append(node)

    return result


def uses_attribute(
    tree: ast.Module,
    root_name: str,
    attribute_name: str,
) -> bool:

    for node in ast.walk(tree):

        if not isinstance(node, ast.Attribute):
            continue

        if node.attr != attribute_name:
            continue

        if (
            isinstance(node.value, ast.Name)
            and node.value.id == root_name
        ):

            return True

    return False


def assigned_names(
    tree: ast.Module,
) -> set[str]:

    result = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            targets = node.targets

        elif isinstance(node, ast.AnnAssign):

            targets = [node.target]

        else:

            continue

        for target in targets:

            if isinstance(target, ast.Name):

                result.add(target.id)

    return result


def make_result(
    status: str,
    details: list[str] | None = None,
) -> dict:

    return {
        "status": status,
        "details": details or [],
    }


# =========================================================
# 1. CONFIGURATION SCHEMA
# =========================================================

def check_config_schema() -> dict:

    result = make_result("PASS")

    if not CONFIG_PATH.is_file():

        return make_result(
            "FAIL",
            ["benchmark_config.json does not exist"],
        )

    try:

        raw = CONFIG_PATH.read_bytes()

        config = json.loads(
            raw.decode("utf-8")
        )

        if not isinstance(config, dict):

            result["details"].append(
                "Configuration root must be a JSON object"
            )

            result["status"] = "FAIL"

            return result

        output_directory = config.get(
            "output_directory"
        )

        if (
            not isinstance(output_directory, str)
            or not output_directory.strip()
        ):

            result["details"].append(
                "output_directory must be a non-empty string"
            )

        artifacts = config.get("artifacts")

        if not isinstance(artifacts, dict):

            result["details"].append(
                "artifacts must be a JSON object"
            )

        else:

            artifact_values = []

            for key in ARTIFACT_KEYS:

                value = artifacts.get(key)

                if (
                    not isinstance(value, str)
                    or not value.strip()
                ):

                    result["details"].append(
                        f"artifacts.{key} must be a non-empty string"
                    )

                else:

                    artifact_values.append(value)

            if (
                len(artifact_values)
                != len(set(artifact_values))
            ):

                result["details"].append(
                    "Artifact filenames must be unique"
                )

        result["sha256"] = hashlib.sha256(
            raw
        ).hexdigest()

    except Exception as exc:

        result["details"].append(
            f"Configuration parsing failed: {exc}"
        )

    if result["details"]:

        result["status"] = "FAIL"

    return result


# =========================================================
# 2. BENCHMARK CONTRACT API
# =========================================================

def check_contract_api() -> dict:

    result = make_result("PASS")

    tree, error = parse_python_file(
        CONTRACT_PATH
    )

    if error:

        return make_result(
            "FAIL",
            [error],
        )

    functions = top_level_functions(tree)

    classes = top_level_classes(tree)

    if "load_benchmark_contract" not in functions:

        result["details"].append(
            "load_benchmark_contract is missing"
        )

    contract_class = classes.get(
        "BenchmarkContract"
    )

    if contract_class is None:

        result["details"].append(
            "BenchmarkContract class is missing"
        )

    else:

        methods = {
            node.name: node
            for node in contract_class.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for property_name in CONTRACT_PROPERTIES:

            node = methods.get(property_name)

            if node is None:

                result["details"].append(
                    f"BenchmarkContract.{property_name} is missing"
                )

                continue

            decorators = {
                decorator.id
                for decorator in node.decorator_list
                if isinstance(decorator, ast.Name)
            }

            if "property" not in decorators:

                result["details"].append(
                    f"BenchmarkContract.{property_name} "
                    "is not a property"
                )

        annotated_fields = {
            node.target.id
            for node in contract_class.body
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
            )
        }

        for field in CONTRACT_FIELDS:

            if field not in annotated_fields:

                result["details"].append(
                    f"BenchmarkContract field {field} is missing"
                )

    # -----------------------------------------------------
    # Runtime signature inspection
    # -----------------------------------------------------

    try:

        sys.path.insert(
            0,
            str(BENCHMARK_DIR),
        )

        spec = importlib.util.spec_from_file_location(
            "p2_audit_contract_runtime",
            CONTRACT_PATH,
        )

        if spec is None or spec.loader is None:

            raise ImportError(
                "Cannot create contract module specification"
            )

        module = importlib.util.module_from_spec(
            spec
        )

        sys.modules[spec.name] = module

        spec.loader.exec_module(module)

        signature = inspect.signature(
            module.load_benchmark_contract
        )

        parameters = list(
            signature.parameters.values()
        )

        if len(parameters) != 2:

            result["details"].append(
                "load_benchmark_contract must have exactly "
                "two parameters"
            )

        else:

            config_parameter = parameters[0]

            root_parameter = parameters[1]

            if (
                config_parameter.name != "config_path"
                or config_parameter.kind
                != inspect.Parameter.POSITIONAL_OR_KEYWORD
            ):

                result["details"].append(
                    "config_path parameter name or kind is incorrect"
                )

            if (
                root_parameter.name != "p2_root"
                or root_parameter.kind
                != inspect.Parameter.KEYWORD_ONLY
            ):

                result["details"].append(
                    "p2_root must be keyword-only"
                )

            for parameter in parameters:

                if (
                    parameter.default
                    is inspect.Parameter.empty
                ):

                    result["details"].append(
                        f"{parameter.name} has no default value"
                    )

                if (
                    parameter.annotation
                    is inspect.Parameter.empty
                ):

                    result["details"].append(
                        f"{parameter.name} has no type annotation"
                    )

        if (
            signature.return_annotation
            is inspect.Signature.empty
        ):

            result["details"].append(
                "load_benchmark_contract has no return annotation"
            )

        for exported_name in (
            "BenchmarkContract",
            "DEFAULT_CONFIG_PATH",
            "assert_cli_output_directory",
        ):

            if not hasattr(module, exported_name):

                result["details"].append(
                    f"Contract export missing: {exported_name}"
                )

        result["runtime_signature"] = str(
            signature
        )

    except Exception as exc:

        result["details"].append(
            f"Runtime contract inspection failed: {exc}"
        )

    if result["details"]:

        result["status"] = "FAIL"

    return result


# =========================================================
# 3. RUNNER INTEGRATION
# =========================================================

def check_runner_integration() -> dict:

    result = make_result("PASS")

    tree, error = parse_python_file(
        RUNNER_PATH
    )

    if error:

        return make_result(
            "FAIL",
            [error],
        )

    imports = imported_names(tree)

    required_imports = (
        "load_benchmark_contract",
        "BenchmarkContract",
        "assert_cli_output_directory",
    )

    for name in required_imports:

        if name not in imports:

            result["details"].append(
                f"Runner does not import {name}"
            )

    contract_calls = calls_named(
        tree,
        "load_benchmark_contract",
    )

    if not contract_calls:

        result["details"].append(
            "Runner never calls load_benchmark_contract"
        )

    config_passed = False

    for call in contract_calls:

        for keyword in call.keywords:

            if keyword.arg == "config_path":

                value = keyword.value

                if (
                    isinstance(value, ast.Attribute)
                    and value.attr == "config"
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "args"
                ):

                    config_passed = True

        for argument in call.args:

            if (
                isinstance(argument, ast.Attribute)
                and argument.attr == "config"
                and isinstance(argument.value, ast.Name)
                and argument.value.id == "args"
            ):

                config_passed = True

    if not config_passed:

        result["details"].append(
            "args.config is not passed to load_benchmark_contract"
        )

    source = RUNNER_PATH.read_text(
        encoding="utf-8"
    )

    if "--config" not in source:

        result["details"].append(
            "Runner does not define --config"
        )

    if not calls_named(
        tree,
        "assert_cli_output_directory",
    ):

        result["details"].append(
            "Runner does not validate CLI output directory"
        )

    forbidden = sorted(
        assigned_names(tree)
        & FORBIDDEN_CONSTANTS
    )

    if forbidden:

        result["details"].append(
            f"Historical artifact constants found: {forbidden}"
        )

    if result["details"]:

        result["status"] = "FAIL"

    return result


# =========================================================
# 4. VALIDATOR INTEGRATION
# =========================================================

def check_validator_integration() -> dict:

    result = make_result("PASS")

    tree, error = parse_python_file(
        VALIDATOR_PATH
    )

    if error:

        return make_result(
            "FAIL",
            [error],
        )

    functions = top_level_functions(tree)

    imports = imported_names(tree)

    for required_function in (
        "validate_results",
        "validate_markdown",
        "main",
    ):

        if required_function not in functions:

            result["details"].append(
                f"Validator function missing: {required_function}"
            )

    if "load_benchmark_contract" not in imports:

        result["details"].append(
            "Validator does not import load_benchmark_contract"
        )

    if not calls_named(
        tree,
        "load_benchmark_contract",
    ):

        result["details"].append(
            "Validator does not call load_benchmark_contract"
        )

    validate_results = functions.get(
        "validate_results"
    )

    if validate_results is not None:

        isolated_tree = ast.Module(
            body=[validate_results],
            type_ignores=[],
        )

        if not uses_attribute(
            isolated_tree,
            "contract",
            "artifact_paths",
        ):

            result["details"].append(
                "validate_results does not use contract.artifact_paths"
            )

    validate_markdown = functions.get(
        "validate_markdown"
    )

    if validate_markdown is not None:

        isolated_tree = ast.Module(
            body=[validate_markdown],
            type_ignores=[],
        )

        if not uses_attribute(
            isolated_tree,
            "contract",
            "artifacts",
        ):

            result["details"].append(
                "validate_markdown does not use contract.artifacts"
            )

    forbidden = sorted(
        assigned_names(tree)
        & FORBIDDEN_CONSTANTS
    )

    if forbidden:

        result["details"].append(
            f"Historical artifact constants found: {forbidden}"
        )

    if result["details"]:

        result["status"] = "FAIL"

    return result


# =========================================================
# 5. MAIN
# =========================================================

def main() -> int:

    checks = {
        "config_schema": check_config_schema(),
        "contract_api": check_contract_api(),
        "runner_integration": check_runner_integration(),
        "validator_integration": check_validator_integration(),
    }

    statuses = [
        check["status"]
        for check in checks.values()
    ]

    if "FAIL" in statuses:

        overall_status = "FAIL"

    elif "NOT VERIFIED" in statuses:

        overall_status = "NOT VERIFIED"

    else:

        overall_status = "PASS"

    report = {
        "audit": "contract_integration",
        "audit_id": "P2-BENCH-CONFIG-01",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "repository": "adrianroman1/QFLPN-Quantum-Petri-Nets",
        "status": overall_status,
        "checks": checks,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    if overall_status == "FAIL":

        return 1

    return 0


if __name__ == "__main__":

    raise SystemExit(main())
