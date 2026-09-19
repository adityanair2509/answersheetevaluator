import requests

url = "http://localhost:8000/api/v1/sheets/12/approve"
data = {"score": 8.5, "question_number": 1, "teacher_id": "teacher1"}
try:
    resp = requests.post(url, json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")
