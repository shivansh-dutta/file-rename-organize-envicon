# DWG File Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two Claude Code slash commands (`/organize-scan` and `/organize-apply`) that convert DWG files to PNG via ODA File Converter + ezdxf, analyze them with Claude's built-in vision, write a `rename_plan.json` manifest for user review, and apply renames/folder organization after confirmation.

**Architecture:** Two Python scripts handle all I/O: `convert_dwg.py` wraps ODA File Converter (DWG→DXF) then ezdxf (DXF→PNG); `apply.py` validates and executes the rename manifest. Two slash command markdown files drive the workflow and provide Claude's AI vision analysis. No external API keys required beyond Claude Code itself.

**Tech Stack:** Python 3, ODA File Converter (system install), ezdxf[draw] + matplotlib, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `.claude/commands/organize-scan.md` | Slash command prompt — drives DWG→PNG conversion loop and vision analysis |
| `.claude/commands/organize-apply.md` | Slash command prompt — runs apply.py dry-run, confirms, then applies |
| `.claude/scripts/convert_dwg.py` | Converts one DWG to PNG: ODA (DWG→DXF), then ezdxf (DXF→PNG); CLI entrypoint |
| `.claude/scripts/apply.py` | Reads manifest, validates, prints summary, moves/renames files, writes log; CLI entrypoint |
| `conftest.py` | Adds `.claude/scripts` to sys.path so tests can import the scripts |
| `requirements.txt` | Python dependencies |
| `tests/test_convert_dwg.py` | Unit tests for convert_dwg.py |
| `tests/test_apply.py` | Unit tests for apply.py |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `conftest.py`
- Create: `tests/__init__.py`
- Create: `tests/test_convert_dwg.py` (empty)
- Create: `tests/test_apply.py` (empty)
- Create: `.claude/commands/` (directory)
- Create: `.claude/scripts/` (directory)
- Create: `.claude/tmp/.gitkeep`

- [ ] **Step 1: Create directories**

```powershell
New-Item -ItemType Directory -Force -Path ".claude\commands", ".claude\scripts", ".claude\tmp", "tests"
New-Item -ItemType File -Force -Path ".claude\tmp\.gitkeep", "tests\__init__.py"
```

Expected: directories and files created, no errors.

- [ ] **Step 2: Write requirements.txt**

```
ezdxf[draw]>=1.1.0
matplotlib>=3.7.0
pytest>=7.4.0
```

- [ ] **Step 3: Install dependencies**

```powershell
pip install -r requirements.txt
```

Expected: packages install successfully.

- [ ] **Step 4: Write conftest.py**

```python
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / ".claude" / "scripts"))


@pytest.fixture(autouse=True)
def restore_cwd():
    """Restore working directory after each test so os.chdir() calls don't leak."""
    original = os.getcwd()
    yield
    os.chdir(original)
```

- [ ] **Step 5: Create empty test stubs**

Create `tests/test_convert_dwg.py`:

```python
# tests/test_convert_dwg.py
```

Create `tests/test_apply.py`:

```python
# tests/test_apply.py
```

- [ ] **Step 6: Verify pytest discovers tests (empty is fine)**

```powershell
pytest tests/ -v
```

Expected: `no tests ran` — 0 errors, 0 failures.

- [ ] **Step 7: Commit**

```powershell
git init
git add .
git commit -m "chore: project scaffold"
```

---

## Task 2: convert_dwg.py — ODA Subprocess Wrapper

**Files:**
- Create: `.claude/scripts/convert_dwg.py`
- Test: `tests/test_convert_dwg.py`

- [ ] **Step 1: Write the failing tests for _run_oda()**

Replace `tests/test_convert_dwg.py`:

```python
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def fake_dwg(tmp_path):
    dwg = tmp_path / "FILE000.dwg"
    dwg.write_bytes(b"fake dwg content")
    return dwg


def test_oda_called_with_correct_arguments(fake_dwg, tmp_path):
    """ODA is invoked with tmp_in, tmp_out, ACAD2018, DXF."""
    from convert_dwg import _run_oda

    tmp_in = tmp_path / "in"
    tmp_out = tmp_path / "out"
    tmp_in.mkdir()
    tmp_out.mkdir()
    # Pre-create the expected DXF so the existence check passes
    (tmp_out / "FILE000.dxf").write_bytes(b"")

    with patch("subprocess.run") as mock_run, patch("shutil.copy2"):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        _run_oda(fake_dwg, tmp_in, tmp_out)

        args = mock_run.call_args[0][0]
        assert str(tmp_in) in args
        assert str(tmp_out) in args
        assert "DXF" in args
        assert "ACAD2018" in args


def test_oda_nonzero_exit_raises(fake_dwg, tmp_path):
    """RuntimeError is raised when ODA exits non-zero."""
    from convert_dwg import _run_oda

    tmp_in = tmp_path / "in"
    tmp_out = tmp_path / "out"
    tmp_in.mkdir()
    tmp_out.mkdir()

    with patch("subprocess.run") as mock_run, patch("shutil.copy2"):
        mock_run.return_value = MagicMock(returncode=1, stderr="ODA exploded")

        with pytest.raises(RuntimeError, match="ODA failed"):
            _run_oda(fake_dwg, tmp_in, tmp_out)


def test_missing_output_dxf_raises(fake_dwg, tmp_path):
    """RuntimeError is raised when ODA exits 0 but produces no DXF."""
    from convert_dwg import _run_oda

    tmp_in = tmp_path / "in"
    tmp_out = tmp_path / "out"
    tmp_in.mkdir()
    tmp_out.mkdir()
    # Do NOT create the DXF file

    with patch("subprocess.run") as mock_run, patch("shutil.copy2"):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with pytest.raises(RuntimeError, match="did not produce"):
            _run_oda(fake_dwg, tmp_in, tmp_out)
```

- [ ] **Step 2: Run tests to verify they fail (ImportError expected)**

```powershell
pytest tests/test_convert_dwg.py -v
```

Expected: all 3 tests fail with `ImportError: No module named 'convert_dwg'`

- [ ] **Step 3: Implement _run_oda() in convert_dwg.py**

Create `.claude/scripts/convert_dwg.py`:

```python
# ============================================================
# CONFIGURATION — update ODA_EXE to match your installation
# ============================================================
ODA_EXE = r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
# ============================================================

import shutil
import subprocess
import sys
from pathlib import Path


def _run_oda(dwg_path: Path, tmp_in: Path, tmp_out: Path) -> Path:
    """Copy DWG to tmp_in, run ODA converter, return path to output DXF."""
    shutil.copy2(dwg_path, tmp_in / dwg_path.name)
    result = subprocess.run(
        [ODA_EXE, str(tmp_in), str(tmp_out), "ACAD2018", "DXF", "0", "1"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ODA failed: {result.stderr}")
    dxf = tmp_out / (dwg_path.stem + ".dxf")
    if not dxf.exists():
        raise RuntimeError(f"ODA did not produce {dxf.name}")
    return dxf


def _render_dxf_to_png(dxf_path: Path, png_path: Path) -> None:
    pass  # implemented in Task 3


def convert_dwg_to_png(dwg_path: str, png_path: str) -> None:
    pass  # implemented in Task 4
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
pytest tests/test_convert_dwg.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/convert_dwg.py tests/test_convert_dwg.py
git commit -m "feat: ODA subprocess wrapper with tests"
```

---

## Task 3: convert_dwg.py — DXF to PNG Rendering

**Files:**
- Modify: `.claude/scripts/convert_dwg.py` (implement `_render_dxf_to_png`)
- Modify: `tests/test_convert_dwg.py` (add rendering test)

- [ ] **Step 1: Add the failing rendering test**

Append to `tests/test_convert_dwg.py`:

```python
def test_render_dxf_to_png_produces_image(tmp_path):
    """A minimal DXF is rendered to a non-empty PNG file."""
    import ezdxf
    from convert_dwg import _render_dxf_to_png

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 100))
    dxf_path = tmp_path / "test.dxf"
    doc.saveas(str(dxf_path))

    png_path = tmp_path / "test.png"
    _render_dxf_to_png(dxf_path, png_path)

    assert png_path.exists()
    assert png_path.stat().st_size > 1000  # real image, not empty
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
pytest tests/test_convert_dwg.py::test_render_dxf_to_png_produces_image -v
```

Expected: FAIL — `_render_dxf_to_png` is a no-op stub

- [ ] **Step 3: Implement _render_dxf_to_png()**

Replace the `_render_dxf_to_png` stub in `.claude/scripts/convert_dwg.py`:

```python
def _render_dxf_to_png(dxf_path: Path, png_path: Path) -> None:
    """Render a DXF file to PNG using ezdxf + matplotlib."""
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend, safe on headless systems
    import matplotlib.pyplot as plt

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)
    fig.savefig(str(png_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
```

- [ ] **Step 4: Run all convert_dwg tests**

```powershell
pytest tests/test_convert_dwg.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/convert_dwg.py tests/test_convert_dwg.py
git commit -m "feat: DXF to PNG rendering via ezdxf"
```

---

## Task 4: convert_dwg.py — Public API, Cleanup, and CLI

**Files:**
- Modify: `.claude/scripts/convert_dwg.py` (implement `convert_dwg_to_png` and `__main__`)
- Modify: `tests/test_convert_dwg.py` (add public API + cleanup tests)

- [ ] **Step 1: Add tests for cleanup and public API**

Append to `tests/test_convert_dwg.py`:

```python
import os


def test_convert_dwg_to_png_calls_render_on_success(fake_dwg, tmp_path):
    """convert_dwg_to_png calls _render_dxf_to_png when ODA succeeds."""
    from convert_dwg import convert_dwg_to_png

    os.chdir(tmp_path)
    fake_dxf = tmp_path / ".claude" / "tmp" / "output" / "FILE000.dxf"

    with patch("convert_dwg._run_oda", return_value=fake_dxf) as mock_oda, \
         patch("convert_dwg._render_dxf_to_png") as mock_render:

        png_out = tmp_path / "out.png"
        convert_dwg_to_png(str(fake_dwg), str(png_out))

        mock_oda.assert_called_once()
        mock_render.assert_called_once()


def test_convert_dwg_to_png_cleans_up_dxf_after_success(fake_dwg, tmp_path):
    """The DXF file returned by _run_oda is deleted after rendering."""
    from convert_dwg import convert_dwg_to_png

    os.chdir(tmp_path)
    fake_dxf = tmp_path / "fake.dxf"
    fake_dxf.write_bytes(b"")

    with patch("convert_dwg._run_oda", return_value=fake_dxf), \
         patch("convert_dwg._render_dxf_to_png"):

        convert_dwg_to_png(str(fake_dwg), str(tmp_path / "out.png"))

    assert not fake_dxf.exists()


def test_convert_dwg_to_png_raises_and_cleans_on_oda_failure(fake_dwg, tmp_path):
    """RuntimeError propagates and no DXF is left behind when ODA fails."""
    from convert_dwg import convert_dwg_to_png

    os.chdir(tmp_path)

    with patch("convert_dwg._run_oda", side_effect=RuntimeError("ODA failed: crash")):
        with pytest.raises(RuntimeError, match="ODA failed"):
            convert_dwg_to_png(str(fake_dwg), str(tmp_path / "out.png"))
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pytest tests/test_convert_dwg.py::test_convert_dwg_to_png_calls_render_on_success tests/test_convert_dwg.py::test_convert_dwg_to_png_cleans_up_dxf_after_success tests/test_convert_dwg.py::test_convert_dwg_to_png_raises_and_cleans_on_oda_failure -v
```

Expected: all 3 FAIL — `convert_dwg_to_png` is a stub

- [ ] **Step 3: Implement convert_dwg_to_png() and CLI in convert_dwg.py**

Replace the `convert_dwg_to_png` stub and add the `__main__` block at the bottom:

```python
def convert_dwg_to_png(dwg_path: str, png_path: str) -> None:
    """Convert a DWG file to PNG. Raises RuntimeError on failure."""
    dwg = Path(dwg_path)
    png = Path(png_path)
    tmp_in = Path(".claude/tmp/input")
    tmp_out = Path(".claude/tmp/output")
    tmp_in.mkdir(parents=True, exist_ok=True)
    tmp_out.mkdir(parents=True, exist_ok=True)

    dxf = None
    try:
        dxf = _run_oda(dwg, tmp_in, tmp_out)
        _render_dxf_to_png(dxf, png)
    finally:
        (tmp_in / dwg.name).unlink(missing_ok=True)
        if dxf and dxf.exists():
            dxf.unlink()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_dwg.py <dwg_path> <png_output_path>", file=sys.stderr)
        sys.exit(1)
    try:
        convert_dwg_to_png(sys.argv[1], sys.argv[2])
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

- [ ] **Step 4: Run all convert_dwg tests**

```powershell
pytest tests/test_convert_dwg.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/convert_dwg.py tests/test_convert_dwg.py
git commit -m "feat: convert_dwg public API and CLI entrypoint"
```

---

## Task 5: apply.py — load_manifest() and validate_manifest()

**Files:**
- Create: `.claude/scripts/apply.py`
- Test: `tests/test_apply.py`

- [ ] **Step 1: Write failing tests for load_manifest and validate_manifest**

Replace `tests/test_apply.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pytest tests/test_apply.py -v
```

Expected: all fail with `ImportError: No module named 'apply'`

- [ ] **Step 3: Implement load_manifest() and validate_manifest() in apply.py**

Create `.claude/scripts/apply.py`:

```python
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

MANIFEST_PATH = "rename_plan.json"
LOG_PATH = "organize_log.txt"


def load_manifest(path: str = MANIFEST_PATH) -> list:
    with open(path) as f:
        data = json.load(f)
    return data["files"]


def validate_manifest(files: list) -> list:
    """Return list of error strings. Empty list means valid."""
    errors = []
    seen = {}
    for entry in files:
        if entry.get("error") or entry.get("skip"):
            continue
        for field in ("original", "proposed_name", "folder"):
            if not entry.get(field):
                errors.append(f"{entry.get('original', '?')}: missing field '{field}'")
        original = entry.get("original", "")
        if original and not Path(original).exists():
            errors.append(f"{original}: file not found")
        dest = f"{entry.get('folder', '')}/{entry.get('proposed_name', '')}"
        if dest in seen:
            errors.append(f"Duplicate destination {dest}: conflicts with {seen[dest]}")
        else:
            seen[dest] = original
    return errors


def build_summary(files: list) -> dict:
    pass  # implemented in Task 6


def apply_renames(files: list) -> list:
    pass  # implemented in Task 7


def write_log(log_entries: list) -> None:
    pass  # implemented in Task 8


def main() -> None:
    pass  # implemented in Task 8
```

- [ ] **Step 4: Run apply tests**

```powershell
pytest tests/test_apply.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/apply.py tests/test_apply.py
git commit -m "feat: apply manifest loading and validation"
```

---

## Task 6: apply.py — build_summary()

**Files:**
- Modify: `.claude/scripts/apply.py` (implement `build_summary`)
- Modify: `tests/test_apply.py` (add summary tests)

- [ ] **Step 1: Add failing tests for build_summary()**

Append to `tests/test_apply.py`:

```python
# ── build_summary ─────────────────────────────────────────────────────────────

def test_build_summary_groups_by_folder():
    from apply import build_summary

    files = [
        {"original": "A.dwg", "proposed_name": "Alpha.dwg", "folder": "Electrical", "confidence": "high"},
        {"original": "B.dwg", "proposed_name": "Beta.dwg",  "folder": "Electrical", "confidence": "high"},
        {"original": "C.dwg", "proposed_name": "Gamma.dwg", "folder": "Structural",  "confidence": "medium"},
    ]
    summary = build_summary(files)
    assert len(summary["Electrical"]) == 2
    assert len(summary["Structural"]) == 1


def test_build_summary_routes_low_confidence_to_uncategorized():
    from apply import build_summary

    files = [
        {"original": "X.dwg", "proposed_name": "Xray.dwg", "folder": "Electrical", "confidence": "low"},
    ]
    summary = build_summary(files)
    assert "Uncategorized" in summary
    assert "Electrical" not in summary


def test_build_summary_excludes_error_and_skip_entries():
    from apply import build_summary

    files = [
        {"original": "BAD.dwg", "proposed_name": "", "folder": "", "confidence": "low", "error": "conversion_failed"},
        {"original": "SKP.dwg", "proposed_name": "S.dwg", "folder": "Elec", "confidence": "high", "skip": True},
    ]
    summary = build_summary(files)
    assert summary == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pytest tests/test_apply.py::test_build_summary_groups_by_folder tests/test_apply.py::test_build_summary_routes_low_confidence_to_uncategorized tests/test_apply.py::test_build_summary_excludes_error_and_skip_entries -v
```

Expected: all 3 FAIL — `build_summary` is a stub returning `None`

- [ ] **Step 3: Implement build_summary()**

Replace the `build_summary` stub in `.claude/scripts/apply.py`:

```python
def build_summary(files: list) -> dict:
    """Return {folder: [(original, proposed_name), ...]} grouped by destination folder."""
    summary = {}
    for entry in files:
        if entry.get("error") or entry.get("skip"):
            continue
        folder = "Uncategorized" if entry.get("confidence") == "low" else entry["folder"]
        summary.setdefault(folder, []).append((entry["original"], entry["proposed_name"]))
    return summary
```

- [ ] **Step 4: Run all apply tests**

```powershell
pytest tests/test_apply.py -v
```

Expected: 8 PASSED

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/apply.py tests/test_apply.py
git commit -m "feat: build_summary groups files by folder"
```

---

## Task 7: apply.py — apply_renames()

**Files:**
- Modify: `.claude/scripts/apply.py` (implement `apply_renames`)
- Modify: `tests/test_apply.py` (add rename execution tests)

- [ ] **Step 1: Add failing tests for apply_renames()**

Append to `tests/test_apply.py`:

```python
# ── apply_renames ─────────────────────────────────────────────────────────────

@pytest.fixture
def workspace(tmp_path):
    """Create a temp workspace with DWG and lock files, cd into it."""
    import os
    (tmp_path / "A.dwg").write_bytes(b"dwg content")
    (tmp_path / "A.dwl").write_bytes(b"lock")
    (tmp_path / "A.dwl2").write_bytes(b"lock2")
    (tmp_path / "B.dwg").write_bytes(b"dwg content")
    os.chdir(tmp_path)
    return tmp_path


def test_apply_renames_moves_file_to_correct_folder(workspace):
    from apply import apply_renames

    files = [
        {"original": "A.dwg", "proposed_name": "Alpha_Plan.dwg", "folder": "Electrical", "confidence": "high"},
    ]
    apply_renames(files)

    assert (workspace / "Electrical" / "Alpha_Plan.dwg").exists()
    assert not (workspace / "A.dwg").exists()


def test_apply_renames_deletes_dwl_lock_files(workspace):
    from apply import apply_renames

    files = [
        {"original": "A.dwg", "proposed_name": "Alpha_Plan.dwg", "folder": "Electrical", "confidence": "high"},
    ]
    apply_renames(files)

    assert not (workspace / "A.dwl").exists()
    assert not (workspace / "A.dwl2").exists()


def test_apply_renames_skips_existing_destination(workspace):
    from apply import apply_renames

    dest_dir = workspace / "Electrical"
    dest_dir.mkdir()
    (dest_dir / "Alpha_Plan.dwg").write_bytes(b"existing")

    files = [
        {"original": "A.dwg", "proposed_name": "Alpha_Plan.dwg", "folder": "Electrical", "confidence": "high"},
    ]
    log = apply_renames(files)

    assert log[0]["status"] == "skipped"
    assert (workspace / "A.dwg").exists()  # original untouched


def test_apply_renames_routes_low_confidence_to_uncategorized(workspace):
    from apply import apply_renames

    files = [
        {"original": "B.dwg", "proposed_name": "Unknown.dwg", "folder": "Electrical", "confidence": "low"},
    ]
    apply_renames(files)

    assert (workspace / "Uncategorized" / "Unknown.dwg").exists()
    assert not (workspace / "Electrical").exists()


def test_apply_renames_returns_log_entries(workspace):
    from apply import apply_renames

    files = [
        {"original": "A.dwg", "proposed_name": "Alpha.dwg", "folder": "Electrical", "confidence": "high"},
        {"original": "B.dwg", "proposed_name": "Beta.dwg",  "folder": "Structural",  "confidence": "high"},
    ]
    log = apply_renames(files)

    assert len(log) == 2
    assert all(e["status"] == "moved" for e in log)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pytest tests/test_apply.py -k "apply_renames" -v
```

Expected: all 5 FAIL — `apply_renames` stub returns `None`

- [ ] **Step 3: Implement apply_renames()**

Replace the `apply_renames` stub in `.claude/scripts/apply.py`:

```python
def apply_renames(files: list) -> list:
    """Move and rename files per manifest. Returns list of log entry dicts."""
    log = []
    for entry in files:
        if entry.get("error") or entry.get("skip"):
            log.append({"status": "skipped", "original": entry["original"], "reason": entry.get("error", "skip flag")})
            continue

        folder = "Uncategorized" if entry.get("confidence") == "low" else entry["folder"]
        dest_dir = Path(folder)
        dest_path = dest_dir / entry["proposed_name"]
        src_path = Path(entry["original"])

        dest_dir.mkdir(exist_ok=True)

        if dest_path.exists():
            log.append({"status": "skipped", "original": entry["original"], "reason": "destination exists", "destination": str(dest_path)})
            continue

        shutil.move(str(src_path), str(dest_path))
        for ext in (".dwl", ".dwl2"):
            lock = src_path.with_suffix(ext)
            if lock.exists():
                lock.unlink()

        log.append({"status": "moved", "original": entry["original"], "destination": str(dest_path)})
    return log
```

- [ ] **Step 4: Run all apply tests**

```powershell
pytest tests/test_apply.py -v
```

Expected: 13 PASSED

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/apply.py tests/test_apply.py
git commit -m "feat: apply_renames moves files and deletes lock files"
```

---

## Task 8: apply.py — write_log(), main(), and CLI

**Files:**
- Modify: `.claude/scripts/apply.py` (implement `write_log`, `main`, `__main__`)
- Modify: `tests/test_apply.py` (add log and CLI tests)

- [ ] **Step 1: Add failing tests for write_log() and main()**

Append to `tests/test_apply.py`:

```python
# ── write_log ─────────────────────────────────────────────────────────────────

def test_write_log_records_moved_and_skipped(workspace):
    from apply import write_log

    log = [
        {"status": "moved",   "original": "A.dwg", "destination": "Electrical/Alpha.dwg"},
        {"status": "skipped", "original": "B.dwg", "reason": "destination exists"},
    ]
    write_log(log)

    content = (workspace / "organize_log.txt").read_text()
    assert "MOVED" in content
    assert "Electrical/Alpha.dwg" in content
    assert "SKIPPED" in content
    assert "destination exists" in content


# ── main (dry-run) ────────────────────────────────────────────────────────────

def test_main_dry_run_prints_summary_and_exits_zero(workspace, capsys, monkeypatch):
    from apply import main

    manifest = [
        {"original": "A.dwg", "proposed_name": "Alpha.dwg", "folder": "Electrical", "confidence": "high"},
    ]
    monkeypatch.setattr("apply.load_manifest", lambda *_: manifest)
    monkeypatch.setattr("sys.argv", ["apply.py"])  # no --apply flag

    main()

    captured = capsys.readouterr()
    assert "Electrical" in captured.out
    assert not (workspace / "Electrical").exists()  # nothing moved


def test_main_apply_flag_executes_renames(workspace, monkeypatch):
    from apply import main

    manifest = [
        {"original": "A.dwg", "proposed_name": "Alpha.dwg", "folder": "Electrical", "confidence": "high"},
    ]
    monkeypatch.setattr("apply.load_manifest", lambda *_: manifest)
    monkeypatch.setattr("sys.argv", ["apply.py", "--apply"])

    main()

    assert (workspace / "Electrical" / "Alpha.dwg").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pytest tests/test_apply.py -k "write_log or main" -v
```

Expected: all 3 FAIL

- [ ] **Step 3: Implement write_log(), main(), and __main__ in apply.py**

Replace the `write_log` and `main` stubs, and add `__main__`, in `.claude/scripts/apply.py`:

```python
def write_log(log_entries: list) -> None:
    lines = [f"DWG File Organizer — {datetime.now().isoformat()}", ""]
    for e in log_entries:
        if e["status"] == "moved":
            lines.append(f"MOVED:   {e['original']} -> {e['destination']}")
        else:
            lines.append(f"SKIPPED: {e['original']} ({e.get('reason', '')})")
    with open(LOG_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    apply_flag = "--apply" in sys.argv

    files = load_manifest()
    errors = validate_manifest(files)
    if errors:
        print("Validation errors — fix rename_plan.json before applying:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    summary = build_summary(files)
    total = sum(len(v) for v in summary.values())
    print(f"\nReady to apply {total} rename(s) across {len(summary)} folder(s):")
    for folder, items in sorted(summary.items()):
        print(f"  {folder}/  ->  {len(items)} file(s)")

    if not apply_flag:
        print("\n(Dry run — no files moved. Run with --apply to execute.)")
        return

    log = apply_renames(files)
    write_log(log)
    moved = sum(1 for e in log if e["status"] == "moved")
    skipped = sum(1 for e in log if e["status"] == "skipped")
    print(f"\nDone: {moved} moved, {skipped} skipped. See {LOG_PATH} for details.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full test suite**

```powershell
pytest tests/ -v
```

Expected: all tests PASSED (no failures)

- [ ] **Step 5: Commit**

```powershell
git add .claude/scripts/apply.py tests/test_apply.py
git commit -m "feat: apply CLI with dry-run and apply modes"
```

---

## Task 9: organize-scan.md Slash Command

**Files:**
- Create: `.claude/commands/organize-scan.md`

- [ ] **Step 1: Write organize-scan.md**

Create `.claude/commands/organize-scan.md`:

````markdown
You are running the `/organize-scan` command for the DWG File Organizer. Follow these steps exactly and in order. Do not skip steps.

## Step 1 — Check for existing manifest

```powershell
Test-Path "rename_plan.json"
```

If the result is `True`, tell the user:
> "rename_plan.json already exists and will be overwritten. Continue? (yes/no)"

Wait for their response. If they say anything other than "yes", stop and tell them: "Scan cancelled. Existing manifest preserved."

## Step 2 — Find DWG files

```powershell
Get-ChildItem -Path . -Filter "*.dwg" -File | Select-Object -ExpandProperty Name | Sort-Object
```

Collect the list of filenames. If none are found, tell the user "No .dwg files found in this directory." and stop.

## Step 3 — Create temp directory

```powershell
New-Item -ItemType Directory -Force -Path ".claude\tmp" | Out-Null
```

## Step 4 — Process each DWG file

Process each file **one at a time** in alphabetical order. For each file, complete steps 4a through 4c before moving to the next file.

### 4a. Convert DWG to PNG

Replace `<filename>` with the actual filename (e.g. `FILE000.dwg`) and `<stem>` with the name without extension (e.g. `FILE000`):

```powershell
python .claude\scripts\convert_dwg.py "<filename>" ".claude\tmp\<stem>.png"
```

If this exits with a non-zero code or prints an error, record the following for this file and move on to the next:
```json
{
  "original": "<filename>",
  "proposed_name": "<filename>",
  "folder": "",
  "description": "Conversion failed — review manually",
  "confidence": "low",
  "error": "conversion_failed"
}
```

### 4b. Analyze the drawing

Read the image at `.claude\tmp\<stem>.png` using your vision capability.

Based on what you see, determine:

- **`proposed_name`**: A descriptive filename in Title_Case with underscores, `.dwg` extension. Use text visible in title blocks, labels, revision notes, or drawing content. Be specific. Example: `Electrical_Panel_Schedule_Level_2.dwg`
- **`folder`**: The most fitting category from: `Electrical`, `Structural`, `Floor Plans`, `Mechanical`, `Site Plans`, `Civil`, `Plumbing`, `Architectural`, `Uncategorized`
- **`description`**: One sentence describing what the drawing shows
- **`confidence`**: `high` if confident, `medium` if mostly sure, `low` if content is unclear or unreadable

### 4c. Delete the temp PNG

```powershell
Remove-Item ".claude\tmp\<stem>.png" -Force -ErrorAction SilentlyContinue
```

## Step 5 — Write rename_plan.json

Use the Write tool to write `rename_plan.json` in the current directory with all collected entries:

```json
{
  "files": [
    {
      "original": "FILE000.dwg",
      "proposed_name": "Site_Plan_Overview.dwg",
      "folder": "Site Plans",
      "description": "Overall site plan showing building footprint and lot lines",
      "confidence": "high"
    }
  ]
}
```

## Step 6 — Report

Tell the user:
> "Scan complete. **N** file(s) analyzed. Manifest written to `rename_plan.json`. Open it, review and edit the proposed names and folders, then run `/organize-apply`."

Replace N with the total count of files processed (including conversion failures).
````

- [ ] **Step 2: Commit**

```powershell
git add .claude/commands/organize-scan.md
git commit -m "feat: /organize-scan slash command"
```

---

## Task 10: organize-apply.md Slash Command

**Files:**
- Create: `.claude/commands/organize-apply.md`

- [ ] **Step 1: Write organize-apply.md**

Create `.claude/commands/organize-apply.md`:

````markdown
You are running the `/organize-apply` command for the DWG File Organizer. Follow these steps exactly and in order.

## Step 1 — Run validation and dry-run summary

```powershell
python .claude\scripts\apply.py
```

Show the complete output to the user.

If the script exits with a non-zero code (validation errors), tell the user:
> "Validation failed. Fix the errors shown above in `rename_plan.json`, then run `/organize-apply` again."

Stop here.

## Step 2 — Ask for confirmation

Tell the user:
> "Does this look right? Reply **yes** to apply all renames, or **no** to cancel and edit `rename_plan.json` further."

If they say anything other than "yes", tell them:
> "Apply cancelled. Edit `rename_plan.json` and run `/organize-apply` again when ready."

Stop here.

## Step 3 — Apply

```powershell
python .claude\scripts\apply.py --apply
```

Show the complete output to the user.
````

- [ ] **Step 2: Run the full test suite one final time**

```powershell
pytest tests/ -v
```

Expected: all tests PASSED

- [ ] **Step 3: Commit**

```powershell
git add .claude/commands/organize-apply.md
git commit -m "feat: /organize-apply slash command — complete"
```

---

## Usage After Implementation

1. Copy the `.claude/` folder into any workspace containing DWG files
2. Open Claude Code in that workspace
3. Run `/organize-scan` — Claude converts and analyzes all DWG files, writes `rename_plan.json`
4. Open and edit `rename_plan.json` in your editor
5. Run `/organize-apply` — review the summary, confirm, files are moved and renamed
6. Check `organize_log.txt` for a full record of what was done
