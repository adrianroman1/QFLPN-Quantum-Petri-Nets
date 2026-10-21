#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
from pathlib import Path


TARGET = Path("P2/benchmarks/validate_benchmark.py")
REPORT = Path("audit/contract_report.json")


def function_nodes(tree: ast.AST) -> dict[str, ast.AST]:
    result = {}

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result[node.name] = node

    return result


def attribute_chain(node: ast.AST) -> tuple[str, ...]:
    parts = []
    current = node

    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value

    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))

    return ()


def has_attribute_chain(
    node: ast.AST,
    expected: tuple[str, ...],
) -> bool:
    return any(
        attribute_chain(item) == expected
        for item in ast.walk(node)
        if isinstance(item, ast.Attribute)
    )


def calls_named(node: ast.AST, name: str) -> list[ast.Call]:
    return [
        item
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and (
            isinstance(item.func, ast.Name)
            and item.func.id == name
            or isinstance(item.func, ast.Attribute)
            and item.func.attr == name
        )
    ]


def string_constants(node: ast.AST) -> set[str]:
    return {
        item.value
        for item in ast.walk(node)
        if isinstance(item, ast.Constant)
        and isinstance(item.value, str)
    }


def main() -> int:
    if not TARGET.is_file():
        print(f"FAIL: missing file: {TARGET}")
        return 1

    try:
        source = TARGET.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(TARGET))
    except (OSError, SyntaxError) as exc:
        print(f"FAIL: {exc}")
        return 1

    functions = function_nodes(tree)

    validate_results = functions.get("validate_results")
    validate_markdown = functions.get("validate_markdown")
    main_function = functions.get("main")

    results_uses_paths = (
        validate_results is not None
        and has_attribute_chain(
            validate_results,
            ("contract", "artifact_paths"),
        )
    )

    markdown_uses_artifacts = (
        validate_markdown is not None
        and has_attribute_chain(
            validate_markdown,
            ("contract", "artifacts"),
        )
    )

    main_loads_contract = (
        main_function is not None
        and bool(
            calls_named(
                main_function,
                "load_benchmark_contract",
            )
        )
    )

    main_checks_results = (
        main_function is not None
        and bool(
            calls_named(
                main_function,
                "assert_cli_output_directory",
            )
        )
    )

    main_strings = (
        string_constants(main_function)
        if main_function is not None
        else set()
    )

    config_cli_declared = "--config" in main_strings
    results_cli_declared = "--results" in main_strings

    results_argument_checked = False

    if main_function is not None:
        for call in calls_named(
            main_function,
            "assert_cli_output_directory",
        ):
            if not call.args:
                continue

            first = call.args[0]

            if (
                isinstance(first, ast.Attribute)
                and first.attr == "results"
                and isinstance(first.value, ast.Name)
                and first.value.id == "args"
            ):
                results_argument_checked = True

    config_argument_loaded = False

    if main_function is not None:
        for call in calls_named(
            main_function,
            "load_benchmark_contract",
        ):
            if not call.args:
                continue

            first = call.args[0]

            if (
                isinstance(first, ast.Attribute)
                and first.attr == "config"
                and isinstance(first.value, ast.Name)
                and first.value.id == "args"
            ):
                config_argument_loaded = True

    checks = {
        "validate_results_uses_contract_artifact_paths":
            results_uses_paths,
        "validate_markdown_uses_contract_artifacts":
            markdown_uses_artifacts,
        "main_loads_benchmark_contract":
            main_loads_contract,
        "main_checks_results_directory":
            main_checks_results,
        "main_declares_config_option":
            config_cli_declared,
        "main_declares_results_option":
            results_cli_declared,
        "assertion_uses_args_results":
            results_argument_checked,
        "loader_uses_args_config":
            config_argument_loaded,
    }

    report = {
        "file": str(TARGET),
        "checks": checks,
        "passed": all(checks.values()),
    }

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(
        "\nCONTRACT REVIEW:",
        "PASS" if report["passed"] else "FAIL",
    )

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
