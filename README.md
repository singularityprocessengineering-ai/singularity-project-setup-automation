# Singularity Project Setup Automation

Utilities for setting up the required Google Drive folder structure for one exact project folder.

## Create project setup folders

The first script creates or reuses only these three folders inside the Google Drive project folder identified by the exact folder URL or folder ID you provide:

- `00_Client_Native_Files`
- `01_AI_LLM_Files`
- `03_References`

The script does not scan Google Drive, guess project names, create any other folders, create reference subfolders, or move/copy/delete/overwrite files. It runs in dry-run mode by default.

### Dry run

```bash
python scripts/create_project_setup_folders.py --project-folder-url "PASTE_PROJECT_FOLDER_URL_HERE"
```

### Apply

Set the Drive webhook credentials, then pass `--apply` to create or reuse the folders:

```bash
export DRIVE_WEBHOOK_URL="PASTE_DRIVE_WEBHOOK_URL_HERE"
export DRIVE_WEBHOOK_API_KEY="PASTE_DRIVE_WEBHOOK_API_KEY_HERE"
python scripts/create_project_setup_folders.py --project-folder-url "PASTE_PROJECT_FOLDER_URL_HERE" --apply
```
