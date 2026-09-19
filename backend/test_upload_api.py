
import requests
import os

def test_upload():
    url = "http://localhost:8000/api/v1/sheets/upload"

    # Create a dummy PDF file
    file_path = "test_sheet.pdf"
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Dummy PDF content")

    try:
        files = [
            ('files', ('test_sheet.pdf', open(file_path, 'rb'), 'application/pdf'))
        ]
        data = {
            'exam_id': 1,
            'student_roll': '2024CS001',
            'is_multi_page': 'false'
        }

        print(f"Sending upload request to {url}...")
        response = requests.post(url, files=files, data=data)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

    except Exception as e:
        print(f"Request failed: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    test_upload()
