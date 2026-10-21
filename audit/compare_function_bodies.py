#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import sys

from pathlib import Path
from typing import Any


EXPECTED_PROTECTED = {
    "finite_number",
    "close",
    "require_number",
    "validate_statistics",
    "validate_world_record",
    "validate_paired_samples",
    "validate_operation",
    "validate_report",
    "validate_csv",
    "markdown_number_matches",
    "validate_environment",
    "remove_benchmark_cache",
}

EXPECTED_CHANGED = {
    "validate_markdown",
    "validate_results",
    "main",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def node_source(
    source: str,
    node: ast.AST,
) -> str:
    result = ast.get_source_segment(
        source,
        node,
    )

    if result is None:
        raise ValueError(
            f"Cannot extract source for {type(node).__name__}"
        )

    return result


def signature_dump(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str:
    return (
        ast.dump(
            node.args,
            annotate_fields=True,
            include_attributes=False,
        )
        + "|returns|"
        + ast.dump(
            node.returns,
            annotate_fields=True,
            include_attributes=False,
        )
    )


def decorator_dump(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    return [
        ast.dump(
            item,
            annotate_fields=True,
            include_attributes=False,
        )
        for item in node.decorator_list
    ]


def collect_functions(
    path: Path,
) -> dict[str, dict[str, Any]]:
    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(path),
    )

    result = {}

    def visit(
        node: ast.AST,
        scope: tuple[str, ...] = (),
    ) -> None:

        if isinstance(node, ast.ClassDef):
            class_scope = (
                scope + (f"class:{node.name}",)
            )

            for child in node.body:
                visit(child, class_scope)

            return

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            qualified_name = ".".join(
                scope + (node.name,)
            )

            if qualified_name in result:
                raise ValueError(
                    f"Duplicate function: {qualified_name}"
                )

            extracted = node_source(
                source,
                node,
            )

            result[qualified_name] = {
                "name": node.name,
                "qualified_name": qualified_name,
                "kind": type(node).__name__,
                "source": extracted,
                "source_sha256": sha256_text(
                    extracted
                ),
                "signature": signature_dump(node),
                "decorators": decorator_dump(node),
                "lineno": node.lineno,
                "end_lineno": node.end_lineno,
            }

            nested_scope = (
                scope + (f"function:{node.name}",)
            )

            for child in node.body:
                visit(child, nested_scope)

            return

        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                visit(child, scope)

    for item in tree.body:
        visit(item)

    return result


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: compare_function_bodies.py "
            "original.py migrated.py"
        )
        return 2

    original_path = Path(sys.argv[1])
    migrated_path = Path(sys.argv[2])

    try:
        original = collect_functions(
            original_path
        )

        migrated = collect_functions(
            migrated_path
        )

    except (
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        print(f"FAIL: {exc}")
        return 1

    original_names = set(original)
    migrated_names = set(migrated)

    missing = sorted(
        original_names - migrated_names
    )

    added = sorted(
        migrated_names - original_names
    )

    identical = []
    changed = []
    signature_changes = []
    decorator_changes = []
    kind_changes = []

    common = sorted(
        original_names & migrated_names
    )

    for name in common:
        old = original[name]
        new = migrated[name]

        if old["source"] == new["source"]:
            identical.append(name)
        else:
            changed.append(name)

        if old["signature"] != new["signature"]:
            signature_changes.append(name)

        if old["decorators"] != new["decorators"]:
            decorator_changes.append(name)

        if old["kind"] != new["kind"]:
            kind_changes.append(name)

    changed_short_names = {
        original[name]["name"]
        for name in changed
    }

    unexpected_changes = sorted(
        changed_short_names - EXPECTED_CHANGED
    )

    expected_change_missing = sorted(
        EXPECTED_CHANGED - changed_short_names
    )

    expected_protected = {
        name
        for name, item in original.items()
        if item["name"] in EXPECTED_PROTECTED
    }

    protected_not_identical = sorted(
        expected_protected - set(identical)
    )

    protected_changed = sorted(
        name
        for name in changed
        if original[name]["name"]
        in EXPECTED_PROTECTED
    )

    protected_missing = sorted(
        name
        for name in missing
        if original[name]["name"]
        in EXPECTED_PROTECTED
    )

    counts = {
        "missing": len(missing),
        "added": len(added),
        "identical": len(identical),
        "changed": len(changed),
        "signature_changes": len(signature_changes),
        "decorator_changes": len(decorator_changes),
        "unexpected_changes": len(unexpected_changes),
    }

    passed = (
        not missing
        and not added
        and not unexpected_changes
        and not expected_change_missing
        and not protected_not_identical
        and not signature_changes
        and not decorator_changes
        and not kind_changes
        and len(original) == 15
        and len(migrated) == 15
        and len(identical) == 12
        and len(changed) == 3
    )

    report = {
        "original_file": str(original_path),
        "migrated_file": str(migrated_path),
        "original_function_count": len(original),
        "migrated_function_count": len(migrated),
        "missing": missing,
        "added": added,
        "identical": identical,
        "changed": changed,
        "signature_changes": signature_changes,
        "decorator_changes": decorator_changes,
        "kind_changes": kind_changes,
        "protected_functions": sorted(
            expected_protected
        ),
        "protected_not_identical": (
            protected_not_identical
        ),
        "protected_changed": protected_changed,
        "protected_missing": protected_missing,
        "unexpected_changes": unexpected_changes,
        "expected_changes_not_found": (
            expected_change_missing
        ),
        "counts": counts,
        "passed": passed,
    }

    output = Path(
        "audit/function_comparison.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
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

    print(
        "\nFUNCTION REVIEW:",
        "PASS" if passed else "FAIL",
    )

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
