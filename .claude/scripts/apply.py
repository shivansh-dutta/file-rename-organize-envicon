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
    """Return {folder: [(original, proposed_name), ...]} grouped by destination folder."""
    summary = {}
    for entry in files:
        if entry.get("error") or entry.get("skip"):
            continue
        folder = "Uncategorized" if entry.get("confidence") == "low" else entry["folder"]
        summary.setdefault(folder, []).append((entry["original"], entry["proposed_name"]))
    return summary


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


def write_log(log_entries: list) -> None:
    pass  # implemented in Task 8


def main() -> None:
    pass  # implemented in Task 8
