import requests
url = 'http://localhost:8000/api/v1/sheets/upload'
file_path = 'D:/PROJECTS/AUTO_SHEET_EVALUATOR/backend/data/uploads/sheet_8/page_1_ScribeScore_Demo_Answer_Sheet.pdf'
with open(file_path, 'rb') as f:
    files = [('files', (file_path, f, 'application/pdf'))]
    data = {'exam_id': '3', 'student_roll': 'AUDIT-001', 'is_multi_page': 'false'}
    r = requests.post(url, files=files, data=data)
    print(r.json())
