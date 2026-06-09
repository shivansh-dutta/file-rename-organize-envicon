# DWG File Organizer

A pair of Claude Code slash commands that analyze AutoCAD DWG files using AI vision, rename them with descriptive names, and organize them into category folders — automatically.

## How it works

1. `/organize-scan` — converts every DWG file to a PNG image, analyzes each one using Claude's built-in vision, and writes a `rename_plan.json` manifest with proposed names and folder categories
2. You review and edit the manifest in any text editor
3. `/organize-apply` — validates the manifest, shows you a summary of what will move, asks for confirmation, then executes all renames and folder moves

Nothing is touched until you confirm. All moves are logged to `organize_log.txt`.

## Requirements

- [Claude Code](https://claude.ai/code)
- Python 3
- [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) (free, converts DWG → DXF)
- Python packages: `pip install -r requirements.txt`

## Setup

**1. Install Python dependencies**

```
pip install -r requirements.txt
```

**2. Configure ODA File Converter path**

Open `.claude/scripts/convert_dwg.py` and update line 3:

```python
ODA_EXE = r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
```

Change this to wherever ODA File Converter is installed on your machine.

**3. Copy `.claude/` into your DWG workspace**

```
your-dwg-folder/
├── .claude/          ← copy this folder here
├── FILE000.dwg
├── FILE001.dwg
└── ...
```

## Usage

Open Claude Code in your DWG folder and run:

```
/organize-scan
```

Claude will process each DWG file one at a time, analyzing the drawings and building a manifest. When it's done, open `rename_plan.json` and review the proposed names and folder assignments.

**`rename_plan.json` example:**
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
    }
  ]
}
```

You can change any `proposed_name` or `folder`, or add `"skip": true` to exclude a file. When ready:

```
/organize-apply
```

Claude runs a dry-run summary first, asks you to confirm, then moves everything.

## Folder categories

Claude will assign each file to one of these folders:

`Electrical` · `Structural` · `Floor Plans` · `Mechanical` · `Site Plans` · `Civil` · `Plumbing` · `Architectural` · `Uncategorized`

Files with low confidence are always placed in `Uncategorized/` regardless of what the manifest says.

## After running

```
your-dwg-folder/
├── Electrical/
│   └── Electrical_Panel_Schedule.dwg
├── Structural/
│   └── Foundation_Plan_Level_1.dwg
├── Floor Plans/
│   └── Ground_Floor_Layout.dwg
├── Uncategorized/
│   └── Unknown_Drawing_03.dwg
├── rename_plan.json      ← kept as a record
└── organize_log.txt      ← full log of every move
```

## Error handling

| Situation | Behavior |
|---|---|
| ODA conversion fails | File flagged in manifest as `"error": "conversion_failed"`, skipped during apply |
| Duplicate destination names | Apply aborts before touching any files, lists the conflicts |
| Destination file already exists | That move is skipped with a warning; rest of apply continues |
| `/organize-scan` run twice | Warns before overwriting existing `rename_plan.json` |

## Development

Tests live in `tests/`. Run with:

```
pytest tests/ -v
```

23 tests covering the conversion pipeline and apply logic.
