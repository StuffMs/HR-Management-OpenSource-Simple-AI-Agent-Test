import os
import sys
from flask import Flask, send_from_directory

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <h1>File Access Test</h1>
    <p>Click the links below to test file access:</p>
    <ul>
        <li><a href="/uploads/documents/temp/certificate_e0846d0a4c37435f88ceaa457b18189a_Sudharsan_Resume.pdf" target="_blank">Local File (documents/temp/certificate_e0846d0a4c37435f88ceaa457b18189a_Sudharsan_Resume.pdf)</a></li>
        <li><a href="/uploads/drive:1Rp9VXssfTnbE5_a7uIzvaqNjO7NiTy_v" target="_blank">Google Drive File (1Rp9VXssfTnbE5_a7uIzvaqNjO7NiTy_v)</a></li>
    </ul>
    """

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    print(f"Accessing file: {filename}")
    
    # Check if it's a Google Drive file ID
    if filename.startswith('drive:'):
        file_id = filename.replace('drive:', '')
        return f"<h1>Google Drive File</h1><p>File ID: {file_id}</p><p>URL: https://drive.google.com/uc?export=download&id={file_id}</p>"
    
    # Handle local files
    if filename.startswith('documents/'):
        # Remove the 'documents/' prefix
        file_path = filename[len('documents/'):]
        upload_path = './static/uploads/documents'
        
        # Handle backslashes in the path
        file_path = file_path.replace('\\', '/')
        
        # Extract the actual filename from the path
        if '/' in file_path:
            parts = file_path.split('/')
            folder_name = parts[0]  # First part is the folder
            filename = parts[-1]    # Last part is the filename
            upload_path = os.path.join(upload_path, *parts[:-1])
        else:
            filename = file_path
    else:
        # Default to documents folder
        upload_path = './static/uploads'
    
    print(f"Upload path: {upload_path}, Filename: {filename}")
    
    try:
        return send_from_directory(upload_path, filename)
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p><p>Path: {os.path.join(upload_path, filename)}</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12000, debug=True)