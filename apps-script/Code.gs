/**
 * Google Apps Script Drive webhook for the project setup automation.
 *
 * This webhook intentionally supports only creating/reusing one explicitly
 * requested child folder under one explicitly provided parent folder.
 */

const API_KEY_PROPERTY = 'DRIVE_WEBHOOK_API_KEY';
const SUPPORTED_ACTION = 'create-folder';
const APPROVED_CALLER = 'project-setup-automation';
const APPROVED_FOLDER_NAMES = [
  '00_Client_Native_Files',
  '01_AI_LLM_Files',
  '03_References',
];

/**
 * Handle POST requests from the GitHub Action folder creation script.
 *
 * @param {Object} e Apps Script event object.
 * @return {GoogleAppsScript.Content.TextOutput} JSON response.
 */
function doPost(e) {
  try {
    const request = parseJsonRequest_(e);
    validateApiKey_(request.api_key);

    if (!request.action) {
      return jsonError_('Missing required field: action.');
    }

    if (request.action !== SUPPORTED_ACTION) {
      return jsonError_(
        'Unsupported action. This webhook only supports create-folder. Delete, move, copy, upload, and overwrite are not supported.'
      );
    }

    return handleCreateFolder_(request);
  } catch (err) {
    return jsonError_(err && err.message ? err.message : String(err));
  }
}

/**
 * Parse and validate a JSON request body.
 *
 * @param {Object} e Apps Script event object.
 * @return {Object} Parsed request payload.
 */
function parseJsonRequest_(e) {
  if (!e || !e.postData || typeof e.postData.contents !== 'string' || !e.postData.contents.trim()) {
    throw new Error('Missing JSON request body.');
  }

  try {
    const parsed = JSON.parse(e.postData.contents);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('JSON request body must be an object.');
    }
    return parsed;
  } catch (err) {
    throw new Error('Invalid JSON request body: ' + (err && err.message ? err.message : String(err)));
  }
}

/**
 * Require the caller-provided API key to match the script property.
 *
 * @param {string} providedApiKey API key from request JSON.
 */
function validateApiKey_(providedApiKey) {
  const expectedApiKey = PropertiesService.getScriptProperties().getProperty(API_KEY_PROPERTY);

  if (!expectedApiKey) {
    throw new Error('Webhook is not configured. Missing Script Property: ' + API_KEY_PROPERTY + '.');
  }

  if (!providedApiKey) {
    throw new Error('Missing required field: api_key.');
  }

  if (String(providedApiKey) !== expectedApiKey) {
    throw new Error('Invalid api_key.');
  }
}

/**
 * Create or reuse an approved child folder inside the provided parent folder.
 *
 * @param {Object} request Parsed request payload.
 * @return {GoogleAppsScript.Content.TextOutput} JSON response.
 */
function handleCreateFolder_(request) {
  const parentFolderId = requireStringField_(request, 'parent_folder_id');
  const folderName = requireStringField_(request, 'folder_name');
  const caller = requireStringField_(request, 'caller');

  if (caller !== APPROVED_CALLER) {
    return jsonError_('Unsupported caller. This webhook only accepts requests from ' + APPROVED_CALLER + '.');
  }

  if (APPROVED_FOLDER_NAMES.indexOf(folderName) === -1) {
    return jsonError_(
      'Unsupported folder_name. This webhook only creates folders requested by the approved project setup script.'
    );
  }

  const parentFolder = DriveApp.getFolderById(parentFolderId);
  const existingFolders = parentFolder.getFoldersByName(folderName);

  if (existingFolders.hasNext()) {
    const existingFolder = existingFolders.next();
    return jsonSuccess_({
      already_existed: true,
      folder_id: existingFolder.getId(),
      folder_url: existingFolder.getUrl(),
      folder_name: existingFolder.getName(),
    });
  }

  const createdFolder = parentFolder.createFolder(folderName);
  return jsonSuccess_({
    already_existed: false,
    folder_id: createdFolder.getId(),
    folder_url: createdFolder.getUrl(),
    folder_name: createdFolder.getName(),
  });
}

/**
 * Read a required non-empty string field from the request.
 *
 * @param {Object} request Parsed request payload.
 * @param {string} fieldName Field to read.
 * @return {string} Trimmed field value.
 */
function requireStringField_(request, fieldName) {
  const value = request[fieldName];
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error('Missing required field: ' + fieldName + '.');
  }
  return value.trim();
}

/**
 * Build a successful JSON response.
 *
 * @param {Object} data Response data.
 * @return {GoogleAppsScript.Content.TextOutput} JSON response.
 */
function jsonSuccess_(data) {
  const payload = Object.assign({ success: true }, data);
  return jsonOutput_(payload);
}

/**
 * Build an error JSON response.
 *
 * @param {string} message Clear user-facing error message.
 * @return {GoogleAppsScript.Content.TextOutput} JSON response.
 */
function jsonError_(message) {
  return jsonOutput_({
    success: false,
    error: message,
  });
}

/**
 * Build a JSON TextOutput response.
 *
 * @param {Object} payload Response payload.
 * @return {GoogleAppsScript.Content.TextOutput} JSON response.
 */
function jsonOutput_(payload) {
  return ContentService
    .createTextOutput(JSON.stringify(payload))
    .setMimeType(ContentService.MimeType.JSON);
}
