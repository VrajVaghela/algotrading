import requests
import pandas as pd
import io

# Create a sample CSV in memory
df = pd.DataFrame({
    'date': pd.date_range(start='2024-01-01', periods=5),
    'open': [100, 101, 102, 101, 103],
    'high': [102, 103, 104, 103, 105],
    'low': [99, 100, 101, 100, 102],
    'close': [101, 102, 101, 103, 104],
    'volume': [1000, 1100, 1200, 1100, 1300]
})

csv_buffer = io.StringIO()
df.to_csv(csv_buffer, index=False)
csv_buffer.seek(0)

# Create a dummy file object
files = {'file': ('test_data.csv', csv_buffer.getvalue())}

try:
    print("Sending POST request to http://127.0.0.1:5000/api/upload ...")
    response = requests.post('http://127.0.0.1:5000/api/upload', files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("SUCCESS: Endpoint is working.")
    else:
        print("FAILURE: Endpoint returned error.")

except Exception as e:
    print(f"ERROR: Failed to connect to server. {e}")
