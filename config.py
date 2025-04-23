import os

# Application configuration
SECRET_KEY = 'your-secret-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///employees.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload size

# Upload directories
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
PROFILE_PICTURES_FOLDER = os.path.join(UPLOAD_FOLDER, 'profile_pictures')
DOCUMENTS_FOLDER = os.path.join(UPLOAD_FOLDER, 'documents')

# Google Drive configuration
GOOGLE_DRIVE_ENABLED = True  # Set to False to disable Google Drive integration
GOOGLE_DRIVE_CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'credentials/google-drive-credentials.json'
)

# Check if credentials file exists
if not os.path.exists(GOOGLE_DRIVE_CREDENTIALS_FILE):
    GOOGLE_DRIVE_ENABLED = False

# Google Drive folder structure
GOOGLE_DRIVE_ROOT_FOLDER_NAME = 'Employee Management System'