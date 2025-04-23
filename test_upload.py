import requests
import os

# URL of the self-onboarding endpoint
url = 'http://localhost:12001/self-onboarding'

# Login first to get a session
login_url = 'http://localhost:12001/login'
login_data = {
    'username': 'testuser',  # Replace with a valid username
    'password': 'password'   # Replace with a valid password
}

# Create a session to maintain cookies
session = requests.Session()

# Login
login_response = session.post(login_url, data=login_data)
print(f"Login status code: {login_response.status_code}")

# Create a test file (20MB)
test_file_path = '/tmp/test_file.pdf'
with open(test_file_path, 'wb') as f:
    f.write(b'0' * (20 * 1024 * 1024))  # 20MB file

# Prepare the form data
form_data = {
    'first_name': 'Test',
    'last_name': 'User',
    'email': 'test@example.com',
    'phone': '1234567890',
    'current_address': '123 Test St',
    'permanent_address': '456 Perm St',
    'department': 'IT',
    'position': 'Developer',
    'employee_id': 'EMP123',
    'education_count': '0',
    'certification_count': '0'
}

# Prepare the files
files = {
    'profile_picture': ('profile.jpg', open(test_file_path, 'rb'), 'image/jpeg'),
    'certificate': ('cert.pdf', open(test_file_path, 'rb'), 'application/pdf'),
}

# Submit the form
response = session.post(url, data=form_data, files=files)
print(f"Upload status code: {response.status_code}")
print(f"Response text: {response.text[:500]}...")  # Print first 500 chars of response

# Clean up
os.remove(test_file_path)