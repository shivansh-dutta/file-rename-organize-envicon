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
