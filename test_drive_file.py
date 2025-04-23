#!/usr/bin/env python3

import os
import sys
from google_drive_helper import GoogleDriveHelper

def test_file_access():
    """Test access to a specific file in Google Drive."""
    # Initialize Google Drive helper
    drive_helper = GoogleDriveHelper()
    
    # File ID from the user's request
    folder_id = "1Rp9VXssfTnbE5_a7uIzvaqNjO7NiTy_v"
    file_name = "certificate_e0846d0a4c37435f88ceaa457b18189a_Sudharsan_Resume.pdf"
    
    print(f"Testing access to file: {file_name} in folder: {folder_id}")
    
    # List files in the folder
    print("\nListing files in folder:")
    files = drive_helper.list_files_in_folder(folder_id)
    if files:
        for file in files:
            file_id = file.get('id')
            name = file.get('name')
            mime_type = file.get('mimeType')
            print(f"- {name} (ID: {file_id}, Type: {mime_type})")
            
            # Get file URLs
            view_url = drive_helper.get_file_url(file_id)
            download_url = drive_helper.get_download_url(file_id)
            print(f"  View URL: {view_url}")
            print(f"  Download URL: {download_url}")
            
            # Make file public
            if drive_helper.make_file_public(file_id):
                print(f"  File {file_id} is now publicly accessible")
    else:
        print("No files found in the folder or folder not found")
    
    # Make the folder public
    if drive_helper.make_file_public(folder_id):
        print(f"\nFolder {folder_id} is now publicly accessible")
    
    # Get folder URL
    folder_url = drive_helper.get_folder_url(folder_id)
    print(f"Folder URL: {folder_url}")

if __name__ == "__main__":
    test_file_access()