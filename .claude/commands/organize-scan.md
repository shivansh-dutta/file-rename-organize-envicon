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
