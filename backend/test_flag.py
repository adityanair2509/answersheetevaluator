import requests

url = "http://localhost:8000/api/v1/sheets/12/flag"
data = {"reason": "Test audit flag", "question_number": 2}
try:
    resp = requests.post(url, json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")
