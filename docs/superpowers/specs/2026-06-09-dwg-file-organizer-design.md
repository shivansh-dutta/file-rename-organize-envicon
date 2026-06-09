# DWG File Organizer — Design Spec
**Date:** 2026-06-09

## Overview

A pair of Claude Code slash commands (`/organize-scan` and `/organize-apply`) that analyze AutoCAD DWG files using Claude's built-in vision, rename them with descriptive names, and organize them into category folders. Designed to be dropped into any folder of DWG files and run immediately.

---

## Goals

- Rename opaquely-named DWG files (e.g. `FILE000.dwg`) to descriptive names based on their visual content
- Organize renamed files into category folders (e.g. `Electrical/`, `Structural/`, `Floor Plans/`)
- Require user review before any files are moved
- Be fully portable — copy `.claude/` into any workspace and it works

---

## Non-Goals

- Does not support non-DWG file types
- Does not modify file contents, only names and locations
- Does not require an external API key beyond what Claude Code already uses

---

## File Structure

```
<target-workspace>/
├── .claude/
│   ├── commands/
│   │   ├── organize-scan.md      ← /organize-scan command definition
│   │   └── organize-apply.md     ← /organize-apply command definition
│   ├── scripts/
│   │   └── convert_dwg.py        ← ODA File Converter wrapper
│   └── tmp/                      ← temporary PNGs (auto-cleaned after scan)
├── rename_plan.json               ← generated manifest (user edits this)
├── organize_log.txt               ← written by apply, record of all moves
├── FILE000.dwg
├── FILE001.dwg
└── ...
```

---

## Dependencies

- **ODA File Converter** — free tool from Open Design Alliance; must be installed on the system. Path to the executable is configured in `convert_dwg.py`.
- **Python 3** — for the conversion wrapper script
- **Claude Code** — provides the vision analysis; no separate Anthropic API key needed beyond what Claude Code already uses

---

## Pipeline

### Phase 1: `/organize-scan`

1. Scan the current working directory for all `.dwg` files (non-recursive)
2. Check if `rename_plan.json` already exists — if so, warn the user before overwriting
3. For each `.dwg` file:
   a. Run ODA File Converter via `convert_dwg.py` → output PNG to `.claude/tmp/<filename>.png`
   b. If conversion fails, record `"error": "conversion_failed"` in the manifest and skip
   c. Claude reads the PNG using its vision capability
   d. Claude determines: proposed filename, folder category, short description, confidence (`high` / `medium` / `low`)
   e. Write the manifest entry immediately (do not batch)
4. Write `rename_plan.json` with all entries
5. Delete all files in `.claude/tmp/`
6. Report: "Manifest written to `rename_plan.json`. Review and edit it, then run `/organize-apply`."

### Phase 2: User edits `rename_plan.json`

User opens `rename_plan.json` in their editor and may:
- Change `proposed_name` for any entry
- Change `folder` for any entry
- Set `"skip": true` on any entry to exclude it from apply
- Leave entries as-is to accept Claude's suggestion

### Phase 3: `/organize-apply`

1. Read and parse `rename_plan.json`
2. Validate:
   - No duplicate `proposed_name` values within the same `folder`
   - All required fields present (`original`, `proposed_name`, `folder`)
   - All `original` files still exist in the current directory
   - Abort with a clear error message if validation fails
3. Show a confirmation summary:
   ```
   Ready to apply N renames across M folders:
     Electrical/       → X files
     Structural/       → Y files
     Uncategorized/    → Z files (low confidence)
   ...
   Confirm? (yes/no)
   ```
4. On confirmation:
   - Create destination folders that don't exist yet
   - For each entry (skipping those with `"skip": true` or `"error"` present):
     - If destination file already exists: skip and warn, do not overwrite
     - Otherwise: move and rename the `.dwg` file
   - Delete `.dwl` and `.dwl2` lock files that share the same base name as moved files
   - Write `organize_log.txt` with a full record of every move (original path → new path)
5. Do not delete `rename_plan.json` — keep it as a record

---

## `rename_plan.json` Schema

```json
{
  "files": [
    {
      "original": "FILE000.dwg",
      "proposed_name": "Site_Plan_Overview.dwg",
      "folder": "Site Plans",
      "description": "Overall site plan showing building footprint and lot lines",
      "confidence": "high"
    },
    {
      "original": "FILE006.dwg",
      "proposed_name": "Electrical_Panel_Schedule.dwg",
      "folder": "Electrical",
      "description": "Panel schedule with circuit breaker layout",
      "confidence": "medium"
    },
    {
      "original": "FILE010.dwg",
      "proposed_name": "Unknown_Drawing_10.dwg",
      "folder": "Uncategorized",
      "description": "Could not determine content with confidence",
      "confidence": "low"
    },
    {
      "original": "FILE003.dwg",
      "proposed_name": "FILE003.dwg",
      "folder": "",
      "description": "",
      "confidence": "low",
      "error": "conversion_failed"
    }
  ]
}
```

**Fields:**
- `original` — original filename, never modified
- `proposed_name` — Claude's suggested name; user may edit
- `folder` — destination folder name; user may edit
- `description` — Claude's description of the drawing content
- `confidence` — `high`, `medium`, or `low`
- `skip` — optional boolean; set to `true` to exclude from apply
- `error` — optional; present if ODA conversion failed

---

## Confidence Handling

- `high` / `medium` → moved to their assigned `folder` value
- `low` → moved to `Uncategorized/` folder; the `folder` field in the manifest reflects what Claude guessed but apply ignores it and uses `Uncategorized/` instead

---

## Error Handling

| Scenario | Behavior |
|---|---|
| ODA conversion fails | Entry flagged with `"error": "conversion_failed"`, skipped in apply, noted in log |
| Duplicate proposed names | Apply aborts before touching any files, lists the conflicts |
| Destination file already exists | That specific move is skipped with a warning; rest of apply continues |
| `/organize-scan` run twice | Warns if `rename_plan.json` exists before overwriting |
| Partial apply failure | `organize_log.txt` records completed moves so user knows where to resume |

---

## Portability

The `.claude/` folder is the only thing that needs to be copied into a workspace. It contains no hardcoded paths except the ODA File Converter executable path in `convert_dwg.py`, which has a clear configuration comment at the top of the file.
