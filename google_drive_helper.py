import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

# Import configuration if available
try:
    import config
    CREDENTIALS_PATH = config.GOOGLE_DRIVE_CREDENTIALS_FILE if config.GOOGLE_DRIVE_ENABLED else None
    ROOT_FOLDER_NAME = config.GOOGLE_DRIVE_ROOT_FOLDER_NAME
except (ImportError, AttributeError):
    CREDENTIALS_PATH = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    ROOT_FOLDER_NAME = 'Employee Management System'

class GoogleDriveHelper:
    def __init__(self, credentials_path=None, root_folder_name=None):
        """
        Initialize the Google Drive helper with service account credentials.
        
        Args:
            credentials_path: Path to the service account credentials JSON file.
                             If None, will use the configured path or GOOGLE_APPLICATION_CREDENTIALS env var.
            root_folder_name: Name of the root folder in Google Drive.
                             If None, will use the configured name.
        """
        self.credentials_path = credentials_path or CREDENTIALS_PATH
        self.root_folder_name = root_folder_name or ROOT_FOLDER_NAME
        self.drive_service = None
        self.root_folder_id = None
        
        # Check if credentials file exists
        if self.credentials_path and os.path.exists(self.credentials_path):
            self._initialize_service()
            if self.is_enabled():
                # Create or get the root folder
                self.root_folder_id = self.create_folder_if_not_exists(self.root_folder_name)
                
                # Make sure the root folder is publicly accessible
                if self.root_folder_id:
                    self.make_file_public(self.root_folder_id)
        else:
            print("Warning: Google Drive credentials not found. File uploads will be stored locally.")
    
    def _initialize_service(self):
        """Initialize the Google Drive service."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=['https://www.googleapis.com/auth/drive']
            )
            self.drive_service = build('drive', 'v3', credentials=credentials)
            print("Google Drive service initialized successfully.")
        except Exception as e:
            print(f"Error initializing Google Drive service: {str(e)}")
            self.drive_service = None
    
    def is_enabled(self):
        """Check if Google Drive integration is enabled."""
        return self.drive_service is not None
    
    def create_folder(self, folder_name, parent_id=None):
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: ID of the parent folder (optional)
            
        Returns:
            Folder ID of the created folder
        """
        if not self.is_enabled():
            return None
            
        try:
            # Create the folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
                
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            
            # Make the folder publicly accessible
            try:
                permission = {'type': 'anyone', 'role': 'reader'}
                self.drive_service.permissions().create(fileId=folder_id, body=permission).execute()
                print(f"Folder {folder_id} is now publicly accessible with a link")
            except Exception as e:
                print(f"Error setting public permission on folder: {str(e)}")
            
            return folder_id
            
        except HttpError as e:
            print(f"Error creating folder in Google Drive: {str(e)}")
            return None
    
    def create_folder_if_not_exists(self, folder_name, parent_id=None):
        """
        Create a folder in Google Drive if it doesn't exist.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: ID of the parent folder (optional)
            
        Returns:
            Folder ID of the created or existing folder
        """
        if not self.is_enabled():
            return None
            
        try:
            # Search for the folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            response = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            # If folder exists, return its ID
            if response.get('files'):
                return response['files'][0]['id']
            
            # If folder doesn't exist, create it
            return self.create_folder(folder_name, parent_id)
            
        except HttpError as e:
            print(f"Error creating folder in Google Drive: {str(e)}")
            return None
    
    def upload_file(self, file_path, file_name=None, parent_folder_id=None, mime_type=None):
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            file_name: Name to give the file in Google Drive (optional)
            parent_folder_id: ID of the parent folder (optional)
            mime_type: MIME type of the file (optional)
            
        Returns:
            File ID of the uploaded file, or None if upload failed
        """
        if not self.is_enabled():
            print("Google Drive is not enabled. Skipping upload.")
            return None
            
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
                
            file_name = file_name or os.path.basename(file_path)
            print(f"Uploading file: {file_path} as {file_name} to folder ID: {parent_folder_id}")
            
            file_metadata = {
                'name': file_name
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            # Check file size
            file_size = os.path.getsize(file_path)
            print(f"File size: {file_size} bytes")
            
            # Use chunked upload for larger files
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            print("Creating file in Google Drive...")
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            print(f"File uploaded successfully. File ID: {file_id}")
            # Make the file publicly accessible
            self._make_uploaded_file_public(file_id)
            
            return file_id
            
        except HttpError as e:
            print(f"HTTP Error uploading file to Google Drive: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error uploading file to Google Drive: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_file_from_memory(self, file_content, file_name, parent_folder_id=None, mime_type=None):
        """
        Upload a file from memory to Google Drive.
        
        Args:
            file_content: File content as bytes or file-like object
            file_name: Name to give the file in Google Drive
            parent_folder_id: ID of the parent folder (optional)
            mime_type: MIME type of the file (optional)
            
        Returns:
            File ID of the uploaded file, or None if upload failed
        """
        if not self.is_enabled():
            print("Google Drive is not enabled. Skipping upload.")
            return None
            
        try:
            print(f"Uploading file from memory: {file_name} to folder ID: {parent_folder_id}")
            
            file_metadata = {
                'name': file_name
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            if isinstance(file_content, bytes):
                file_content = io.BytesIO(file_content)
                
            # Use chunked upload for better reliability
            media = MediaIoBaseUpload(
                file_content,
                mimetype=mime_type,
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            print("Creating file in Google Drive...")
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            print(f"File uploaded successfully. File ID: {file_id}")
            # Make the file publicly accessible
            self._make_uploaded_file_public(file_id)
            
            return file_id
            
        except HttpError as e:
            print(f"HTTP Error uploading file to Google Drive: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error uploading file to Google Drive: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_file_url(self, file_id):
        """
        Get the URL for a file in Google Drive.
        
        Args:
            file_id: ID of the file
            
        Returns:
            URL of the file
        """
        if not file_id:
            return None
            
        return f"https://drive.google.com/file/d/{file_id}/view"
        
    def get_download_url(self, file_id):
        """
        Get the direct download URL for a file in Google Drive.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Direct download URL of the file
        """
        if not file_id:
            return None
            
        return f"https://drive.google.com/uc?export=download&id={file_id}"
        
    def is_file_in_folder(self, file_id, folder_id):
        """
        Check if a file is in a specific folder.
        
        Args:
            file_id: ID of the file
            folder_id: ID of the folder
            
        Returns:
            True if the file is in the folder, False otherwise
        """
        if not self.is_enabled() or not file_id or not folder_id:
            return False
            
        try:
            # Get the file metadata
            file = self.drive_service.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()
            
            # Check if the folder is in the parents
            return folder_id in file.get('parents', [])
            
        except Exception as e:
            print(f"Error checking if file is in folder: {str(e)}")
            # If there's an error, assume the file is accessible
            return True
    
    def get_folder_url(self, folder_id):
        """
        Get the URL for a folder in Google Drive.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            URL of the folder
        """
        if not folder_id:
            return None
            
        return f"https://drive.google.com/drive/folders/{folder_id}"
        
    def make_file_public(self, file_id):
        """
        Make a file publicly accessible with a link.
        
        Args:
            file_id: ID of the file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled() or not file_id:
            return False
            
        try:
            permission = {'type': 'anyone', 'role': 'reader'}
            self.drive_service.permissions().create(fileId=file_id, body=permission).execute()
            print(f"File {file_id} is now publicly accessible with a link")
            return True
        except Exception as e:
            print(f"Error setting public permission: {str(e)}")
            return False
            
    def _make_uploaded_file_public(self, file_id):
        """
        Internal method to make a newly uploaded file public.
        Called automatically after file uploads.
        
        Args:
            file_id: ID of the file
        """
        if file_id:
            try:
                self.make_file_public(file_id)
            except Exception as e:
                print(f"Error making uploaded file public: {str(e)}")
                import traceback
                traceback.print_exc()
                
    def list_files_in_folder(self, folder_id):
        """
        List all files in a Google Drive folder.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            List of file metadata dictionaries, or None if error
        """
        if not self.is_enabled() or not folder_id:
            return None
            
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, webViewLink)",
                pageSize=100
            ).execute()
            
            files = results.get('files', [])
            print(f"Found {len(files)} files in folder {folder_id}")
            return files
            
        except Exception as e:
            print(f"Error listing files in folder: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# Create a singleton instance
# Note: This singleton is not used in app.py, which creates its own instance
drive_helper = GoogleDriveHelper()