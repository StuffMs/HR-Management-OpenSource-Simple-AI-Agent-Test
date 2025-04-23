import sys
from app import drive_helper

def make_all_public():
    """Make all files and folders in Google Drive public."""
    if not drive_helper or not drive_helper.is_enabled():
        print("Google Drive is not enabled.")
        return
    
    # Get all files and folders
    try:
        # Get all files
        results = drive_helper.drive_service.files().list(
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print('No files found.')
            return
            
        print(f'Found {len(items)} files/folders:')
        
        # Make each item public
        for item in items:
            item_id = item['id']
            name = item['name']
            mime_type = item['mimeType']
            
            item_type = "Folder" if mime_type == 'application/vnd.google-apps.folder' else "File"
            print(f"Making {item_type} '{name}' (ID: {item_id}) public...")
            
            drive_helper.make_file_public(item_id)
            
        print("All files and folders are now publicly accessible with a link.")
        
    except Exception as e:
        print(f"Error making files public: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    make_all_public()