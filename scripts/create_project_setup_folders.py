#!/usr/bin/env python3
"""Create the required setup folders inside one exact Google Drive project folder.

The script is intentionally narrow in scope: it only operates on the project
folder ID supplied by the caller and only creates/reuses the three required
folders listed in REQUIRED_FOLDERS. Dry-run mode is the default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

CALLER_NAME = "project-setup-automation"
REQUIRED_FOLDERS = [
    "00_Client_Native_Files",
    "01_AI_LLM_Files",
    "03_References",
]

DRIVE_FOLDER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")


class ScriptError(Exception):
    """A user-facing error that should stop the script cleanly."""


@dataclass
class FolderResult:
    name: str
    status: str
    message: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or reuse the required setup folders inside one exact "
            "Google Drive project folder. Dry-run mode is used unless --apply "
            "is provided."
        )
    )
    parser.add_argument(
        "--project-folder-url",
        required=True,
        help="Exact Google Drive project folder URL, or a raw Google Drive folder ID.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually call the Drive webhook to create/reuse folders.",
    )
    return parser.parse_args()


def extract_folder_id(project_folder_url: str) -> str:
    """Extract and validate a Google Drive folder ID from a URL or raw ID."""
    value = project_folder_url.strip()
    if not value:
        raise ScriptError("Missing project folder URL or folder ID.")

    if DRIVE_FOLDER_ID_RE.fullmatch(value):
        return value

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ScriptError(
            "Invalid project folder URL or folder ID. Provide a Google Drive folders URL "
            "or a raw folder ID."
        )

    path = unquote(parsed.path)
    match = re.search(r"/folders/([A-Za-z0-9_-]+)", path)
    if not match:
        raise ScriptError(
            "Invalid Google Drive folder URL. Expected a URL containing '/drive/folders/FOLDER_ID'."
        )

    folder_id = match.group(1)
    if not DRIVE_FOLDER_ID_RE.fullmatch(folder_id):
        raise ScriptError("Invalid Google Drive folder ID extracted from URL.")

    return folder_id


def require_apply_environment() -> tuple[str, str]:
    webhook_url = os.environ.get("DRIVE_WEBHOOK_URL", "").strip()
    api_key = os.environ.get("DRIVE_WEBHOOK_API_KEY", "").strip()

    missing = []
    if not webhook_url:
        missing.append("DRIVE_WEBHOOK_URL")
    if not api_key:
        missing.append("DRIVE_WEBHOOK_API_KEY")
    if missing:
        raise ScriptError(
            "Missing required environment variable(s) for --apply: " + ", ".join(missing)
        )

    return webhook_url, api_key


def webhook_request(
    webhook_url: str,
    api_key: str,
    project_folder_id: str,
    folder_name: str,
) -> dict[str, Any]:
    payload = {
        "action": "create-folder",
        "caller": CALLER_NAME,
        "parent_folder_id": project_folder_id,
        "folder_name": folder_name,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": api_key,
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            if not response_body.strip():
                return {"ok": True, "status": "created", "message": "Webhook returned an empty success response."}
            try:
                data = json.loads(response_body)
            except json.JSONDecodeError as exc:
                raise ScriptError(
                    f"Webhook returned non-JSON response for '{folder_name}': {response_body}"
                ) from exc
            if not isinstance(data, dict):
                raise ScriptError(f"Webhook returned unexpected JSON for '{folder_name}': {data!r}")
            return data
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise ScriptError(
            f"Webhook HTTP failure for '{folder_name}' ({exc.code} {exc.reason}): {response_body}"
        ) from exc
    except URLError as exc:
        raise ScriptError(f"Webhook connection failure for '{folder_name}': {exc.reason}") from exc
    except TimeoutError as exc:
        raise ScriptError(f"Webhook timed out for '{folder_name}'.") from exc


def normalize_webhook_result(folder_name: str, data: dict[str, Any]) -> FolderResult:
    """Map common webhook response shapes into a stable report status."""
    if data.get("ok") is False or data.get("success") is False or data.get("error"):
        message = str(data.get("error") or data.get("message") or "Webhook reported failure.")
        return FolderResult(folder_name, "failed", message)

    raw_status = str(data.get("status") or data.get("result") or "").strip().lower()
    created = data.get("created")
    already_existed = data.get("already_existed") or data.get("existed")

    if raw_status in {"already_exists", "already existed", "exists", "reused"} or already_existed:
        status = "already existed"
    elif raw_status in {"created", "success", "ok"} or created is True:
        status = "created"
    elif raw_status:
        status = raw_status.replace("_", " ")
    else:
        # A 2xx webhook response without an explicit status is considered a successful reuse/create
        # operation, but we cannot safely claim which happened.
        status = "completed"

    message = str(data.get("message") or data.get("folder_id") or "")
    return FolderResult(folder_name, status, message)


def print_summary(results: list[FolderResult]) -> None:
    print("\nFinal summary:")
    for result in results:
        suffix = f" - {result.message}" if result.message else ""
        print(f"- {result.name}: {result.status}{suffix}")

    failed = sum(1 for result in results if result.status == "failed")
    created = sum(1 for result in results if result.status == "created")
    existed = sum(1 for result in results if result.status == "already existed")
    other = len(results) - failed - created - existed
    print(
        f"Totals: {created} created, {existed} already existed, "
        f"{failed} failed, {other} other."
    )


def run() -> int:
    try:
        args = parse_args()
        project_folder_id = extract_folder_id(args.project_folder_url)

        print(f"Project folder ID: {project_folder_id}")
        print("Required folders:")
        for folder_name in REQUIRED_FOLDERS:
            print(f"- {folder_name}")

        if not args.apply:
            print("\nDry run: no webhook calls will be made and no folders will be created.")
            print("The script would create or reuse these folders inside the provided project folder:")
            results = [
                FolderResult(folder_name, "would create or reuse")
                for folder_name in REQUIRED_FOLDERS
            ]
            print_summary(results)
            return 0

        webhook_url, api_key = require_apply_environment()
        print("\nApply mode: calling Drive webhook to create or reuse folders.")

        results: list[FolderResult] = []
        for folder_name in REQUIRED_FOLDERS:
            try:
                data = webhook_request(webhook_url, api_key, project_folder_id, folder_name)
                result = normalize_webhook_result(folder_name, data)
            except ScriptError as exc:
                result = FolderResult(folder_name, "failed", str(exc))
            results.append(result)
            suffix = f" - {result.message}" if result.message else ""
            print(f"{folder_name}: {result.status}{suffix}")

        print_summary(results)
        return 1 if any(result.status == "failed" for result in results) else 0
    except ScriptError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
