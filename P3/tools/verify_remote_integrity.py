#!/usr/bin/env python3
"""Verify every manifest-listed P3 blob against the remote Git reference."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_PATH = "P3/MANIFEST.txt"
CHECKSUMS_PATH = "P3/SHA256SUMS.txt"


class RemoteIntegrityError(RuntimeError):
    """Raised when remote P3 inventory or content is not verifiable."""


def git(
    root: Path,
    *arguments: str,
    check: bool = True,
) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RemoteIntegrityError(
            f"git {' '.join(arguments)} failed: {message}"
        )
    return result.stdout


def validate_relative_path(value: str) -> None:
    if not value or "\\" in value:
        raise RemoteIntegrityError(f"Invalid manifest path: {value!r}")

    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != value
        or not value.startswith("P3/")
        or value.strip() != value
        or path.name in {"MANIFEST.txt", "SHA256SUMS.txt"}
    ):
        raise RemoteIntegrityError(
            f"Unsafe or noncanonical P3 path: {value!r}"
        )


def parse_manifest(raw: bytes) -> list[str]:
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RemoteIntegrityError(
            "Remote MANIFEST.txt is not UTF-8"
        ) from exc

    if not content.endswith("\n"):
        raise RemoteIntegrityError(
            "Remote MANIFEST.txt has no final newline"
        )

    entries = content.splitlines()
    if not entries or any(not item for item in entries):
        raise RemoteIntegrityError(
            "Remote MANIFEST.txt is empty or contains blank entries"
        )
    if entries != sorted(entries):
        raise RemoteIntegrityError(
            "Remote MANIFEST.txt entries are not sorted"
        )
    if len(entries) != len(set(entries)):
        raise RemoteIntegrityError(
            "Remote MANIFEST.txt contains duplicate paths"
        )

    for entry in entries:
        validate_relative_path(entry)

    return entries


def parse_checksums(raw: bytes) -> dict[str, str]:
    try:
        content = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise RemoteIntegrityError(
            "Remote SHA256SUMS.txt is not ASCII"
        ) from exc

    if not content.endswith("\n"):
        raise RemoteIntegrityError(
            "Remote SHA256SUMS.txt has no final newline"
        )

    result: dict[str, str] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if not match:
            raise RemoteIntegrityError(
                f"Malformed SHA256SUMS.txt line {line_number}"
            )

        digest, path = match.groups()
        validate_relative_path(path)

        if not HEX64.fullmatch(digest):
            raise RemoteIntegrityError(
                f"Invalid SHA-256 digest on line {line_number}"
            )
        if path in result:
            raise RemoteIntegrityError(
                f"Duplicate checksum path: {path}"
            )

        result[path] = digest

    if not result:
        raise RemoteIntegrityError(
            "Remote SHA256SUMS.txt contains no entries"
        )
    if list(result) != sorted(result):
        raise RemoteIntegrityError(
            "Remote SHA256SUMS.txt entries are not sorted"
        )

    return result


def remote_blob(root: Path, ref: str, path: str) -> bytes:
    """Read a path as a blob from the fetched remote commit."""
    object_name = f"{ref}:{path}"
    type_bytes = git(
        root,
        "cat-file",
        "-t",
        object_name,
        check=False,
    )
    if type_bytes.strip() != b"blob":
        raise RemoteIntegrityError(
            f"Remote path is missing or is not a blob: {path}"
        )

    return git(root, "show", object_name)


def verify_remote(
    root: Path,
    *,
    remote: str = "origin",
    branch: str = "main",
) -> dict[str, Any]:
    root = Path(root).resolve()
    if not root.is_dir():
        raise RemoteIntegrityError(
            f"Repository root does not exist: {root}"
        )

    if not re.fullmatch(r"[A-Za-z0-9._/-]+", remote) or remote.startswith("-"):
        raise RemoteIntegrityError(f"Invalid Git remote name: {remote!r}")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or branch.startswith("-"):
        raise RemoteIntegrityError(f"Invalid branch name: {branch!r}")
    if ".." in PurePosixPath(branch).parts:
        raise RemoteIntegrityError(f"Unsafe branch name: {branch!r}")

    git(
        root,
        "fetch",
        "--no-tags",
        remote,
        f"refs/heads/{branch}",
    )

    fetched_ref = "FETCH_HEAD"
    manifest_raw = remote_blob(root, fetched_ref, MANIFEST_PATH)
    checksums_raw = remote_blob(root, fetched_ref, CHECKSUMS_PATH)

    manifest = parse_manifest(manifest_raw)
    checksums = parse_checksums(checksums_raw)

    manifest_set = set(manifest)
    checksum_set = set(checksums)
    if manifest_set != checksum_set:
        missing = sorted(manifest_set - checksum_set)
        extra = sorted(checksum_set - manifest_set)
        raise RemoteIntegrityError(
            "Remote manifest/checksum path sets differ; "
            f"missing_checksums={missing}; extra_checksums={extra}"
        )

    verified: list[dict[str, str]] = []
    for path in manifest:
        content = remote_blob(root, fetched_ref, path)
        actual = hashlib.sha256(content).hexdigest()
        expected = checksums[path]

        if actual != expected:
            raise RemoteIntegrityError(
                f"Remote SHA-256 mismatch for {path}: "
                f"expected {expected}, got {actual}"
            )

        verified.append({
            "path": path,
            "sha256": actual,
            "status": "PASS",
        })

    commit = git(
        root,
        "rev-parse",
        "--verify",
        f"{fetched_ref}^{{commit}}",
    ).decode("ascii").strip()

    return {
        "schema": "qflpn-p3-remote-integrity-v1",
        "validation": "PASS",
        "remote": remote,
        "branch": branch,
        "commit": commit,
        "manifest_path": MANIFEST_PATH,
        "checksums_path": CHECKSUMS_PATH,
        "manifest_entries": len(manifest),
        "verified_remote_blobs": len(verified),
        "files": verified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify every file in the remote P3 manifest against "
            "the remote SHA256SUMS inventory."
        )
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    try:
        result = verify_remote(
            args.root,
            remote=args.remote,
            branch=args.branch,
        )
        rendered = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"

        if args.json_output:
            destination = args.json_output
            if destination.is_symlink():
                raise RemoteIntegrityError(
                    f"Refusing JSON output symlink: {destination}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
        print(
            "P3_REMOTE_INTEGRITY: PASS "
            f"({result['verified_remote_blobs']} remote blobs)"
        )
        return 0

    except (OSError, RemoteIntegrityError, ValueError) as exc:
        failure = {
            "schema": "qflpn-p3-remote-integrity-v1",
            "validation": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }
        rendered = json.dumps(failure, indent=2) + "\n"

        if args.json_output:
            try:
                args.json_output.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                args.json_output.write_text(
                    rendered,
                    encoding="utf-8",
                )
            except OSError as output_error:
                print(
                    f"Cannot write failure JSON: {output_error}",
                    file=sys.stderr,
                )

        print(rendered, file=sys.stderr, end="")
        print(f"P3_REMOTE_INTEGRITY: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
