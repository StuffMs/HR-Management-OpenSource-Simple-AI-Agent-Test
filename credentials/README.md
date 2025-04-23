# Google Drive API Credentials Setup

To enable Google Drive integration for file uploads, follow these steps to set up your Google Drive API credentials:

## 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API for your project

## 2. Create a Service Account

1. In your Google Cloud project, go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Enter a name and description for your service account
4. Grant the service account the following roles:
   - "Drive File Creator" (for creating files)
   - "Drive Folder Creator" (for creating folders)
   - "Drive Metadata Reader" (for reading file metadata)
5. Click "Done"

## 3. Create and Download Service Account Key

1. In the service account list, find the service account you just created
2. Click the three dots menu and select "Manage keys"
3. Click "Add Key" > "Create new key"
4. Select "JSON" as the key type and click "Create"
5. The key file will be downloaded to your computer

## 4. Add the Key to This Application

1. Rename the downloaded JSON key file to `google-drive-credentials.json`
2. Place the file in this directory (`/workspace/Temp/credentials/`)
3. Make sure the file has appropriate permissions (readable by the application)

## 5. Configuration Options

The application will automatically detect and use the credentials file if it's named `google-drive-credentials.json` and placed in this directory.

You can also configure the Google Drive integration in the `config.py` file:

```python
# Google Drive configuration
GOOGLE_DRIVE_ENABLED = True  # Set to False to disable Google Drive integration
GOOGLE_DRIVE_CREDENTIALS_FILE = '/path/to/credentials/google-drive-credentials.json'
GOOGLE_DRIVE_ROOT_FOLDER_NAME = 'Employee Management System'  # Root folder name in Google Drive
```

## 6. Security Notes

- Keep your service account key secure and never commit it to version control
- Restrict the service account permissions to only what's necessary
- Consider using environment variables for sensitive configuration
- The application will fall back to local storage if Google Drive credentials are not found