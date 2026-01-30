import requests
import os

# Read the reproduce_issue.csv file content
file_path = 'reproduce_issue.csv'
with open(file_path, 'rb') as f:
    files = {'file': ('reproduce_issue.csv', f)}
    
    try:
        print("Sending POST request to http://127.0.0.1:5000/api/upload with problematic CSV...")
        response = requests.post('http://127.0.0.1:5000/api/upload', files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"ERROR: Failed to connect to server. {e}")
