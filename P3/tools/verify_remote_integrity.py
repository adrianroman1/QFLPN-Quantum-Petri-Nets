#!/usr/bin/env python3
"""Verify remote P3 integrity and bind published evidence to one CI run.

The remote commit must contain:
- a canonical P3/MANIFEST.txt;
- a matching P3/SHA256SUMS.txt;
- every manifest-listed blob with its declared SHA-256;
- P3/reports/evidence-consistency.json with validation=PASS and the
  exact expected RUN_ID and SOURCE_COMMIT.

The remote publication commit is intentionally distinct from SOURCE_COMMIT:
the former contains the published evidence; the latter identifies the
source revision that produced the evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_RE = re.compile(r"^p3-[0-9]+-[0-9]+$")
MANIFEST_PATH = "P3/MANIFEST.txt"
CHECKSUMS_PATH = "P3/SHA256SUMS.txt"
EVIDENCE_PATH = "P3/reports/evidence-consistency.json"
SCHEMA = "qflpn-p3-remote-integrity-v2"
EVIDENCE_SCHEMA = "qflpn-p3-evidence-consistency-v1"


class RemoteIntegrityError(RuntimeError):
    """Raised when remote P3 inventory, content, or provenance is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RemoteIntegrityError(message)


def git(root: Path, *arguments: str, check: bool = True) -> bytes:
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


def validate_expected_identity(run_id: str, source_commit: str) -> None:
    require(
        isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id) is not None,
        f"Invalid RUN_ID: {run_id!r}; expected p3-<run_id>-<run_attempt>",
    )
    require(
        isinstance(source_commit, str)
        and HEX40.fullmatch(source_commit) is not None,
        "SOURCE_COMMIT must be a 40-character lowercase Git SHA-1",
    )


def validate_relative_path(value: str) -> None:
    require(bool(value), "Manifest path must not be empty")
    require("\\" not in value, f"Backslash in manifest path: {value!r}")

    path = PurePosixPath(value)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and path.as_posix() == value
        and value.startswith("P3/")
        and value.strip() == value
        and path.name not in {"MANIFEST.txt", "SHA256SUMS.txt"},
        f"Unsafe or noncanonical P3 path: {value!r}",
    )


def parse_manifest(raw: bytes) -> list[str]:
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RemoteIntegrityError(
            "Remote MANIFEST.txt is not UTF-8"
        ) from exc

    require(
        content.endswith("\n"),
        "Remote MANIFEST.txt has no final newline",
    )
    entries = content.splitlines()
    require(
        bool(entries) and all(entries),
        "Remote MANIFEST.txt is empty or contains blank entries",
    )
    require(
        entries == sorted(entries),
        "Remote MANIFEST.txt entries are not sorted",
    )
    require(
        len(entries) == len(set(entries)),
        "Remote MANIFEST.txt contains duplicate paths",
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

    require(
        content.endswith("\n"),
        "Remote SHA256SUMS.txt has no final newline",
    )

    result: dict[str, str] = {}
    for line_number, line in enumerate(content.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(
            match is not None,
            f"Malformed SHA256SUMS.txt line {line_number}",
        )
        assert match is not None
        digest, path = match.groups()
        validate_relative_path(path)
        require(
            HEX64.fullmatch(digest) is not None,
            f"Invalid SHA-256 digest on line {line_number}",
        )
        require(
            path not in result,
            f"Duplicate checksum path: {path}",
        )
        result[path] = digest

    require(
        bool(result),
        "Remote SHA256SUMS.txt contains no entries",
    )
    require(
        list(result) == sorted(result),
        "Remote SHA256SUMS.txt entries are not sorted",
    )
    return result


def remote_blob(root: Path, ref: str, path: str) -> bytes:
    """Read a regular Git blob from the fetched remote commit."""
    object_name = f"{ref}:{path}"
    object_type = git(
        root,
        "cat-file",
        "-t",
        object_name,
        check=False,
    )
    require(
        object_type.strip() == b"blob",
        f"Remote path is missing or is not a blob: {path}",
    )
    return git(root, "show", object_name)


def parse_evidence_consistency(
    raw: bytes,
    *,
    expected_run_id: str,
    expected_source_commit: str,
) -> dict[str, Any]:
    try:
        evidence = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RemoteIntegrityError(
            f"Remote evidence-consistency report is invalid JSON: {exc}"
        ) from exc

    require(
        isinstance(evidence, dict),
        "Remote evidence-consistency report must be a JSON object",
    )
    require(
        evidence.get("schema") == EVIDENCE_SCHEMA,
        "Remote evidence-consistency schema mismatch",
    )
    require(
        evidence.get("validation") == "PASS",
        "Remote evidence-consistency validation is not PASS",
    )
    require(
        evidence.get("run_id") == expected_run_id,
        "Remote evidence-consistency RUN_ID mismatch: "
        f"expected {expected_run_id!r}, "
        f"got {evidence.get('run_id')!r}",
    )
    require(
        evidence.get("source_commit") == expected_source_commit,
        "Remote evidence-consistency SOURCE_COMMIT mismatch: "
        f"expected {expected_source_commit!r}, "
        f"got {evidence.get('source_commit')!r}",
    )

    return evidence


def verify_remote(
    root: Path,
    *,
    run_id: str,
    source_commit: str,
    remote: str = "origin",
    branch: str = "main",
) -> dict[str, Any]:
    """Fetch and verify remote P3 integrity and CI provenance."""
    root = Path(root).resolve()
    require(root.is_dir(), f"Repository root does not exist: {root}")
    validate_expected_identity(run_id, source_commit)

    require(
        bool(re.fullmatch(r"[A-Za-z0-9._/-]+", remote))
        and not remote.startswith("-"),
        f"Invalid Git remote name: {remote!r}",
    )
    require(
        bool(re.fullmatch(r"[A-Za-z0-9._/-]+", branch))
        and not branch.startswith("-")
        and ".." not in PurePosixPath(branch).parts,
        f"Invalid branch name: {branch!r}",
    )

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
    require(
        manifest_set == checksum_set,
        "Remote manifest/checksum path sets differ; "
        f"missing_checksums={sorted(manifest_set - checksum_set)}; "
        f"extra_checksums={sorted(checksum_set - manifest_set)}",
    )
    require(
        EVIDENCE_PATH in manifest_set,
        f"Remote manifest does not include {EVIDENCE_PATH}",
    )

    verified: list[dict[str, str]] = []
    evidence_raw: bytes | None = None

    for path in manifest:
        content = remote_blob(root, fetched_ref, path)
        actual = hashlib.sha256(content).hexdigest()
        expected = checksums[path]

        require(
            actual == expected,
            f"Remote SHA-256 mismatch for {path}: "
            f"expected {expected}, got {actual}",
        )

        verified.append({
            "path": path,
            "sha256": actual,
            "status": "PASS",
        })
        if path == EVIDENCE_PATH:
            evidence_raw = content

    require(
        evidence_raw is not None,
        f"Remote evidence report could not be read: {EVIDENCE_PATH}",
    )
    evidence = parse_evidence_consistency(
        evidence_raw,
        expected_run_id=run_id,
        expected_source_commit=source_commit,
    )

    commit = git(
        root,
        "rev-parse",
        "--verify",
        f"{fetched_ref}^{{commit}}",
    ).decode("ascii").strip()
    require(
        HEX40.fullmatch(commit) is not None,
        "Fetched remote reference did not resolve to a valid commit",
    )

    return {
        "schema": SCHEMA,
        "validation": "PASS",
        "remote": remote,
        "branch": branch,
        "commit": commit,
        "run_id": run_id,
        "source_commit": source_commit,
        "evidence_consistency": {
            "path": EVIDENCE_PATH,
            "schema": evidence["schema"],
            "validation": evidence["validation"],
            "run_id": evidence["run_id"],
            "source_commit": evidence["source_commit"],
            "status": "PASS",
        },
        "manifest_path": MANIFEST_PATH,
        "checksums_path": CHECKSUMS_PATH,
        "manifest_entries": len(manifest),
        "verified_remote_blobs": len(verified),
        "files": verified,
    }


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Write JSON atomically and refuse symlink destinations."""
    path = Path(path)
    require(
        not path.is_symlink(),
        f"Refusing JSON output symlink: {path}",
    )
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
            json.dump(
                value,
                stream,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify remote P3 manifest/checksums and bind published "
            "evidence to the expected RUN_ID and SOURCE_COMMIT."
        )
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--run-id", default=os.environ.get("RUN_ID"))
    parser.add_argument(
        "--source-commit",
        default=os.environ.get("SOURCE_COMMIT"),
    )
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    try:
        require(args.run_id, "--run-id or RUN_ID is required")
        require(
            args.source_commit,
            "--source-commit or SOURCE_COMMIT is required",
        )

        result = verify_remote(
            args.root,
            remote=args.remote,
            branch=args.branch,
            run_id=args.run_id,
            source_commit=args.source_commit,
        )
        rendered = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"

        if args.json_output:
            atomic_write_json(args.json_output, result)

        print(rendered, end="")
        print(
            "P3_REMOTE_INTEGRITY: PASS "
            f"({result['verified_remote_blobs']} remote blobs; "
            f"RUN_ID={args.run_id}; SOURCE_COMMIT={args.source_commit})"
        )
        return 0

    except (
        OSError,
        RemoteIntegrityError,
        ValueError,
        TypeError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        failure = {
            "schema": SCHEMA,
            "validation": "FAIL",
            "run_id": args.run_id,
            "source_commit": args.source_commit,
            "error": f"{type(exc).__name__}: {exc}",
        }
        rendered = json.dumps(
            failure,
            indent=2,
            ensure_ascii=False,
        ) + "\n"

        if args.json_output:
            try:
                atomic_write_json(args.json_output, failure)
            except (OSError, RemoteIntegrityError) as output_error:
                print(
                    f"Cannot write failure JSON: {output_error}",
                    file=sys.stderr,
                )

        print(rendered, file=sys.stderr, end="")
        print(f"P3_REMOTE_INTEGRITY: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
