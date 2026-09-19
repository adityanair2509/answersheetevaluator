const BASE_URL = '/api/v1';

export const apiClient = {
  async get(endpoint) {
    const response = await fetch(`${BASE_URL}${endpoint}`);
    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      throw new Error(errText || `API GET request failed: ${response.statusText}`);
    }
    return response.json();
  },
  
  async delete(endpoint) {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      throw new Error(errText || `API DELETE request failed: ${response.statusText}`);
    }
    return response.json();
  },
  
  async post(endpoint, data) {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      throw new Error(errText || `API POST request failed: ${response.statusText}`);
    }
    return response.json();
  },

  async upload(endpoint, formData) {
    const response = await fetch(`${BASE_URL}${endpoint}`, {
      method: 'POST',
      body: formData, // fetch automatically sets Content-Type to multipart/form-data with boundaries
    });
    if (!response.ok) {
      let errDetail = response.statusText;
      try {
        const text = await response.text();
        try {
          const json = JSON.parse(text);
          if (json.detail) errDetail = json.detail;
        } catch (_) {
          if (text) errDetail = text;
        }
      } catch (e) { /* body unreadable, use statusText */ }
      throw new Error(errDetail);
    }
    return response.json();
  }
};

export const AppApi = {
  getTeachers: () => apiClient.get('/teachers'),
  getPreviewExam: () => apiClient.get('/schema-preview/exam'),
  getPreviewEvaluation: () => apiClient.get('/schema-preview/evaluation'),
  getPreviewProcessingJob: () => apiClient.get('/schema-preview/processing-job'),
  
  getDashboardStats: () => apiClient.get('/exams/stats').catch(() => null),
  getRecentBatches: () => apiClient.get('/exams/recent').catch(() => []),
  uploadAnswerSheets: (formData) => apiClient.upload('/sheets/upload', formData),
  getSheetReview: (sheetId) => apiClient.get(`/sheets/${sheetId}/review`).catch(() => null),
  approveScore: (sheetId, score, teacherId, questionNumber) => apiClient.post(`/sheets/${sheetId}/approve`, { score, teacher_id: teacherId, question_number: questionNumber }),
  flagIssue: (sheetId, reason, questionNumber) => apiClient.post(`/sheets/${sheetId}/flag`, { reason, question_number: questionNumber }),

  getExamQuestions: (examId = 1) => apiClient.get(`/exams/${examId}/questions`).catch(() => []),
  addExamQuestion: (examId, data) => apiClient.post(`/exams/${examId}/questions`, data),
  getMyResults: () => apiClient.get('/exams/results').catch(() => []),
  createExam: (data) => apiClient.post('/exams', data),
  uploadReferenceDocument: (examId, formData) => apiClient.upload(`/exams/${examId}/reference`, formData),
  syncToLms: (examId, provider, courseId) => apiClient.post(`/exams/${examId}/lms-sync`, { provider, course_id: courseId }),
  requestReevaluation: (sheetId, reason) => apiClient.post(`/sheets/${sheetId}/reevaluate`, { reason }),
  getReevaluations: () => apiClient.get('/sheets/reevaluations').catch(() => []),
  dismissReevaluation: (evalId) => apiClient.delete(`/sheets/reevaluations/${evalId}`),
  exportExamResults: (examId) => apiClient.get(`/exams/${examId}/export`),
  getGradedSheets: (status = 'ALL') => apiClient.get(`/sheets/list?status=${status}`).catch(() => []),
  getScoreAnalytics: () => apiClient.get('/exams/analytics').catch(() => null),
  clearAllData: () => apiClient.delete('/exams/data/clear'),
};
