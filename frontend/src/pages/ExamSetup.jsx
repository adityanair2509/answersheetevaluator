import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Plus, Save, AlertCircle, Loader2 } from 'lucide-react';
import { AppApi } from '../api/client';
import './Upload.css'; // Reuse upload styles for now

const ExamSetup = () => {
  const navigate = useNavigate();
  const [examTitle, setExamTitle] = useState('');
  const [courseCode, setCourseCode] = useState('');
  const [questions, setQuestions] = useState([
    { question_number: 1, question_text: '', expected_answer: '', max_marks: 10 }
  ]);
  const [referenceFile, setReferenceFile] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleAddQuestion = () => {
    setQuestions(prev => [
      ...prev, 
      { 
        question_number: prev.length + 1, 
        question_text: '', 
        expected_answer: '', 
        max_marks: 10 
      }
    ]);
  };

  const handleQuestionChange = (index, field, value) => {
    const newQuestions = [...questions];
    newQuestions[index][field] = value;
    setQuestions(newQuestions);
  };

  const handleRemoveQuestion = (index) => {
    if (questions.length === 1) return;
    const newQuestions = questions.filter((_, i) => i !== index).map((q, i) => ({
      ...q,
      question_number: i + 1
    }));
    setQuestions(newQuestions);
  };

  const handleSaveExam = async () => {
    if (!examTitle.trim()) {
      setError("Please provide an Exam Title.");
      return;
    }
    
    // Validate questions
    for (let q of questions) {
      if (!q.question_text.trim()) {
        setError(`Question ${q.question_number} is missing text.`);
        return;
      }
      if (!q.expected_answer.trim()) {
        setError(`Question ${q.question_number} is missing the expected answer key.`);
        return;
      }
    }

    setIsSaving(true);
    setError(null);
    setSuccess(null);

    try {
      // 1. Create Exam
      const exam = await AppApi.createExam({
        title: examTitle,
        course_code: courseCode
      });

      // 2. Add Questions
      for (let q of questions) {
        await AppApi.addExamQuestion(exam.id, {
          question_number: q.question_number,
          question_text: q.question_text,
          expected_answer: q.expected_answer,
          max_marks: parseFloat(q.max_marks),
          rubric_hints: "Standard grading"
        });
      }

      // 3. Upload Reference Document if present
      if (referenceFile) {
        const formData = new FormData();
        formData.append('file', referenceFile);
        await AppApi.uploadReferenceDocument(exam.id, formData);
      }

      setSuccess(`Exam "${exam.title}" created successfully with ID: ${exam.id}`);
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to create exam.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="upload-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>Create New Exam</h1>
          <p className="subtitle">Define the Question Paper and Answer Key for students.</p>
        </div>
      </header>

      {error && (
        <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.5rem', borderColor: 'var(--error-color)', color: 'var(--error-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.5rem', borderColor: 'var(--success-color)', color: 'var(--success-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Save size={20} />
          <span>{success}</span>
        </div>
      )}

      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Exam Details</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Exam Title *</label>
            <input 
              type="text" 
              value={examTitle} 
              onChange={(e) => setExamTitle(e.target.value)}
              placeholder="e.g. Midterm Physics"
              style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Course Code</label>
            <input 
              type="text" 
              value={courseCode} 
              onChange={(e) => setCourseCode(e.target.value)}
              placeholder="e.g. PHY101"
              style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}
            />
          </div>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Reference Materials (Optional)</h3>
        <div>
          <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Upload Textbook Chapter or Syllabus (PDF)</label>
          <input 
            type="file" 
            accept=".pdf,.txt"
            onChange={(e) => setReferenceFile(e.target.files[0])}
            style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}
          />
          <p style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            This document will be vectorised and stored in ChromaDB. The AI will retrieve relevant sections automatically during evaluation to award partial credit based on course materials.
          </p>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', margin: 0 }}>Question Paper & Answer Key</h3>
          <button className="btn-secondary" onClick={handleAddQuestion} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
            <Plus size={16} /> Add Question
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {questions.map((q, index) => (
            <div key={index} style={{ padding: '1.5rem', border: '1px solid var(--border-glass)', borderRadius: '8px', background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h4 style={{ margin: 0, color: 'var(--accent-primary)' }}>Question {q.question_number}</h4>
                {questions.length > 1 && (
                  <button onClick={() => handleRemoveQuestion(index)} style={{ background: 'none', border: 'none', color: 'var(--error-color)', cursor: 'pointer', fontSize: '0.85rem', textDecoration: 'underline' }}>
                    Remove
                  </button>
                )}
              </div>
              
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Question Text *</label>
                <textarea 
                  value={q.question_text} 
                  onChange={(e) => handleQuestionChange(index, 'question_text', e.target.value)}
                  placeholder="Enter the question..."
                  rows={3}
                  style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Expected Answer (Key) *</label>
                  <textarea 
                    value={q.expected_answer} 
                    onChange={(e) => handleQuestionChange(index, 'expected_answer', e.target.value)}
                    placeholder="Enter the ideal answer..."
                    rows={4}
                    style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)', resize: 'vertical' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Max Marks</label>
                  <input 
                    type="number" 
                    min="1"
                    step="0.5"
                    value={q.max_marks} 
                    onChange={(e) => handleQuestionChange(index, 'max_marks', e.target.value)}
                    style={{ width: '100%', padding: '0.6rem 0.8rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
        <button 
          className="btn-primary" 
          onClick={handleSaveExam}
          disabled={isSaving}
          style={{ padding: '0.8rem 2rem', fontSize: '1rem' }}
        >
          {isSaving ? (
            <><Loader2 size={18} className="animate-spin" /> Saving Exam...</>
          ) : (
            <><BookOpen size={18} /> Publish Exam</>
          )}
        </button>
      </div>
    </div>
  );
};

export default ExamSetup;
