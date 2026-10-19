import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from P1.tools.compute_checksums import inventory_files, sha256_bytes


def test_sha256_helper_matches_standard_library():
    payload = b"QFLPN-P1-checksum-test\x00"
    assert sha256_bytes(payload) == hashlib.sha256(payload).hexdigest()


def test_inventory_is_sorted_and_excludes_self_referential_files():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "P1" / "tools").mkdir(parents=True)
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "P1" / "a.txt").write_text("a", encoding="utf-8")
        (root / "P1" / "MANIFEST.txt").write_text("self", encoding="utf-8")
        (root / "P1" / "SHA256SUMS.txt").write_text("self", encoding="utf-8")
        (root / "P1" / "tools" / "b.py").write_text("b", encoding="utf-8")
        (root / ".github" / "workflows" / "ci.yml").write_text("c", encoding="utf-8")
        files = inventory_files(root)
        names = [p.relative_to(root).as_posix() for p in files]
        assert names == sorted(names)
        assert "P1/MANIFEST.txt" not in names
        assert "P1/SHA256SUMS.txt" not in names
        assert set(names) == {"P1/a.txt", "P1/tools/b.py", ".github/workflows/ci.yml"}
