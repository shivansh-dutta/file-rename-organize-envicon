import json
import shutil
from pathlib import Path

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def manifest_file(tmp_path):
    """Write a minimal rename_plan.json and return its path."""
    data = {
        "files": [
            {"original": "A.dwg", "proposed_name": "Alpha.dwg", "folder": "Electrical", "confidence": "high"},
            {"original": "B.dwg", "proposed_name": "Beta.dwg",  "folder": "Structural",  "confidence": "medium"},
        ]
    }
    p = tmp_path / "rename_plan.json"
    p.write_text(json.dumps(data))
    return p


# ── load_manifest ─────────────────────────────────────────────────────────────

def test_load_manifest_returns_files_list(manifest_file):
    from apply import load_manifest
    files = load_manifest(str(manifest_file))
    assert len(files) == 2
    assert files[0]["original"] == "A.dwg"


# ── validate_manifest ─────────────────────────────────────────────────────────

def test_validate_manifest_passes_for_existing_files(tmp_path):
    from apply import validate_manifest

    (tmp_path / "A.dwg").write_bytes(b"")
    (tmp_path / "B.dwg").write_bytes(b"")

    import os
    os.chdir(tmp_path)

    files = [
        {"original": "A.dwg", "proposed_name": "Alpha.dwg", "folder": "Elec", "confidence": "high"},
        {"original": "B.dwg", "proposed_name": "Beta.dwg",  "folder": "Struct", "confidence": "high"},
    ]
    assert validate_manifest(files) == []


def test_validate_manifest_detects_duplicate_destinations(tmp_path):
    from apply import validate_manifest

    (tmp_path / "A.dwg").write_bytes(b"")
    (tmp_path / "B.dwg").write_bytes(b"")

    import os
    os.chdir(tmp_path)

    files = [
        {"original": "A.dwg", "proposed_name": "Same.dwg", "folder": "Elec", "confidence": "high"},
        {"original": "B.dwg", "proposed_name": "Same.dwg", "folder": "Elec", "confidence": "high"},
    ]
    errors = validate_manifest(files)
    assert any("Duplicate" in e for e in errors)


def test_validate_manifest_detects_missing_original(tmp_path):
    from apply import validate_manifest

    import os
    os.chdir(tmp_path)

    files = [
        {"original": "MISSING.dwg", "proposed_name": "Foo.dwg", "folder": "Elec", "confidence": "high"},
    ]
    errors = validate_manifest(files)
    assert any("not found" in e for e in errors)


def test_validate_manifest_skips_error_and_skip_entries(tmp_path):
    from apply import validate_manifest

    import os
    os.chdir(tmp_path)

    files = [
        {"original": "BAD.dwg", "proposed_name": "", "folder": "", "confidence": "low", "error": "conversion_failed"},
        {"original": "SKIP.dwg", "proposed_name": "X.dwg", "folder": "Elec", "confidence": "high", "skip": True},
    ]
    # Neither file exists on disk, but both should be ignored by validation
    assert validate_manifest(files) == []
