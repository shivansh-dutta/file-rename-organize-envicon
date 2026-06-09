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
