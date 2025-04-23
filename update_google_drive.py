#!/usr/bin/env python3

import re

# Read the file
with open('google_drive_helper.py', 'r') as f:
    content = f.read()

# Pattern to find the return statement in upload_file method
pattern1 = r'(print\(f"File uploaded successfully\. File ID: {file_id}"\)\s+)return file_id'

# Replace with call to make file public
replacement1 = r'\1# Make the file publicly accessible\n            self._make_uploaded_file_public(file_id)\n            \n            return file_id'

# Apply the replacement
modified_content = re.sub(pattern1, replacement1, content)

# Write the modified content back to the file
with open('google_drive_helper.py', 'w') as f:
    f.write(modified_content)

print("File updated successfully.")
