# Google Drive webhook deployment

This Google Apps Script webhook creates or reuses the approved Google Drive setup folders when called by the GitHub Action.

## Deploy the webhook

1. Open [Google Apps Script](https://script.google.com/).
2. Create a new project.
3. Paste the contents of `Code.gs` into the project's `Code.gs` file.
4. Add a Script Property named `DRIVE_WEBHOOK_API_KEY`:
   - In the Apps Script editor, open **Project Settings**.
   - Under **Script properties**, click **Add script property**.
   - Set **Property** to `DRIVE_WEBHOOK_API_KEY`.
   - Set **Value** to a strong secret API key.
5. Deploy the project as a Web App:
   - Click **Deploy** > **New deployment**.
   - Choose **Web app**.
   - Set **Execute as** to the account that should create folders in Drive.
   - Set **Who has access** to the appropriate access level for your organization.
   - Click **Deploy** and authorize the script when prompted.
6. Copy the Web App URL from the deployment details.
7. Add the Web App URL to GitHub Secrets as `DRIVE_WEBHOOK_URL`.
8. Add the same API key from the Script Property to GitHub Secrets as `DRIVE_WEBHOOK_API_KEY`.

## Supported request

The webhook only supports the `create-folder` action from the approved project setup automation caller. It does not support delete, move, copy, upload, overwrite, or arbitrary folder creation.

Example JSON body:

```json
{
  "api_key": "YOUR_SECRET_API_KEY",
  "action": "create-folder",
  "caller": "project-setup-automation",
  "parent_folder_id": "GOOGLE_DRIVE_PARENT_FOLDER_ID",
  "folder_name": "00_Client_Native_Files"
}
```

Successful responses include:

- `success`
- `already_existed`
- `folder_id`
- `folder_url`
- `folder_name`

Error responses include `success: false` and a clear `error` message.
