#!/usr/bin/env python3

from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Drive File Viewer Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .file-container { margin: 20px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            iframe { width: 100%; height: 600px; border: 1px solid #ddd; }
            .buttons { margin: 10px 0; }
            .btn { padding: 8px 15px; margin-right: 10px; background-color: #4285f4; color: white; 
                   border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background-color: #3367d6; }
        </style>
    </head>
    <body>
        <h1>Google Drive File Viewer Test</h1>
        
        <div class="file-container">
            <h2>PDF File Test</h2>
            <p>File ID: 13z4QzYSYbDQPbs9DoPKYYTTf6bAToicx</p>
            <p>File Name: certificate_e0846d0a4c37435f88ceaa457b18189a_Sudharsan_Resume.pdf</p>
            
            <div class="buttons">
                <a href="https://drive.google.com/file/d/13z4QzYSYbDQPbs9DoPKYYTTf6bAToicx/view" target="_blank" class="btn">View in Google Drive</a>
                <a href="https://drive.google.com/uc?export=download&id=13z4QzYSYbDQPbs9DoPKYYTTf6bAToicx" class="btn">Download</a>
            </div>
            
            <h3>Embedded View:</h3>
            <iframe src="https://drive.google.com/file/d/13z4QzYSYbDQPbs9DoPKYYTTf6bAToicx/preview" allow="autoplay"></iframe>
        </div>
        
        <div class="file-container">
            <h2>Image File Test</h2>
            <p>File ID: 1JQ1SHjdU5xhiOtQWsBH-TnSQ2ND-TDKz</p>
            <p>File Name: 28d4f7660b4c4ec18d8e60996ea4608b_Screenshot_2025-04-22_170544.jpg</p>
            
            <div class="buttons">
                <a href="https://drive.google.com/file/d/1JQ1SHjdU5xhiOtQWsBH-TnSQ2ND-TDKz/view" target="_blank" class="btn">View in Google Drive</a>
                <a href="https://drive.google.com/uc?export=download&id=1JQ1SHjdU5xhiOtQWsBH-TnSQ2ND-TDKz" class="btn">Download</a>
            </div>
            
            <h3>Embedded View:</h3>
            <iframe src="https://drive.google.com/file/d/1JQ1SHjdU5xhiOtQWsBH-TnSQ2ND-TDKz/preview" allow="autoplay"></iframe>
        </div>
        
        <div class="file-container">
            <h2>Folder Test</h2>
            <p>Folder ID: 1Rp9VXssfTnbE5_a7uIzvaqNjO7NiTy_v</p>
            
            <div class="buttons">
                <a href="https://drive.google.com/drive/folders/1Rp9VXssfTnbE5_a7uIzvaqNjO7NiTy_v" target="_blank" class="btn">View Folder in Google Drive</a>
            </div>
            
            <h3>Embedded View:</h3>
            <iframe src="https://drive.google.com/embeddedfolderview?id=1Rp9VXssfTnbE5_a7uIzvaqNjO7NiTy_v#list" allow="autoplay"></iframe>
        </div>
    </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12001, debug=True)