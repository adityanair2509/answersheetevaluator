import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, File, X, AlertCircle, Loader2, Zap } from 'lucide-react';
import { AppApi } from '../api/client';
import './Upload.css';

const ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png'];
const MAX_BATCH_SIZE = 50;

const Upload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [examId, setExamId] = useState('1');
  const [studentRoll, setStudentRoll] = useState('2024CS001');
  const [isMultiPage, setIsMultiPage] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processedFileCount, setProcessedFileCount] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);

  const navigate = useNavigate();
  const progressIntervalRef = useRef(null);
  const blobUrlsRef = useRef([]);

  // Cleanup interval and blob URLs on unmount
  useEffect(() => {
    return () => {
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
      blobUrlsRef.current.forEach(url => URL.revokeObjectURL(url));
    };
  }, []);

  const validateFiles = (fileList, currentFiles) => {
    const valid = [];
    let invalidCount = 0;

    fileList.forEach(file => {
      const ext = file.name.split('.').pop().toLowerCase();
      if (ALLOWED_EXTENSIONS.includes(ext)) {
        valid.push(file);
      } else {
        invalidCount++;
      }
    });

    const totalAllowed = MAX_BATCH_SIZE - currentFiles.length;
    if (valid.length > totalAllowed) {
      setErrorMessage(`Batch upload limit is 50 files. First ${totalAllowed} file(s) were added to the batch.`);
      return valid.slice(0, Math.max(0, totalAllowed));
    }

    if (invalidCount > 0) {
      setErrorMessage(`Rejected ${invalidCount} unsupported file(s). Only PDF, JPG, and PNG files are allowed.`);
    } else {
      setErrorMessage(null);
    }

    return valid;
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const validFiles = validateFiles(droppedFiles, files);
      setFiles((prev) => [...prev, ...validFiles]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      const validFiles = validateFiles(selectedFiles, files);
      setFiles((prev) => [...prev, ...validFiles]);
    }
  };

  const load50SampleBatch = () => {
    const sampleBatch = [];
    for (let i = 1; i <= 50; i++) {
      const dummyContent = `Sample Exam Sheet #${i}\nStudent Roll: 2024CS${String(i).padStart(3, '0')}`;
      const blob = new Blob([dummyContent], { type: 'text/plain' });
      const file = new File([blob], `answer_sheet_student_${String(i).padStart(2, '0')}.pdf`, { type: 'application/pdf' });
      sampleBatch.push(file);
    }
    setFiles(sampleBatch);
    setErrorMessage(null);
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAllFiles = () => {
    setFiles([]);
    setErrorMessage(null);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setErrorMessage("Please select between 1 to 50 answer sheet files to evaluate.");
      return;
    }

    setUploading(true);
    setErrorMessage(null);
    setUploadProgress(10);
    setProcessedFileCount(1);

    const totalFiles = files.length;

    // Progress interval using ref for reliable cleanup
    progressIntervalRef.current = setInterval(() => {
      setProcessedFileCount((prevCount) => {
        const next = prevCount + 1;
        if (next >= totalFiles) {
          clearInterval(progressIntervalRef.current);
          progressIntervalRef.current = null;
          setUploadProgress(100);
          return totalFiles;
        }
        setUploadProgress(Math.round((next / totalFiles) * 100));
        return next;
      });
    }, Math.max(100, Math.round(1500 / totalFiles)));

    const formData = new FormData();
    formData.append('exam_id', examId);
    formData.append('student_roll', studentRoll);
    formData.append('is_multi_page', isMultiPage);
    files.forEach(file => formData.append('files', file));

    try {
      const response = await AppApi.uploadAnswerSheets(formData);

      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      setUploadProgress(100);

      // Revoke previously created blob URLs before creating new ones
      blobUrlsRef.current.forEach(url => URL.revokeObjectURL(url));
      const uploadedFileUrls = files.map(f => URL.createObjectURL(f));
      blobUrlsRef.current = uploadedFileUrls;
      const uploadedFileTypes = files.map(f => f.type);

      if (uploadedFileUrls.length > 0) {
        sessionStorage.setItem('previewFileUrls', JSON.stringify(uploadedFileUrls));
        sessionStorage.setItem('previewFileTypes', JSON.stringify(uploadedFileTypes));
        // Fallback for old single-file components
        sessionStorage.setItem('previewFileUrl', uploadedFileUrls[0]);
        sessionStorage.setItem('previewFileType', uploadedFileTypes[0]);
      }

      if (!response || !response.sheet_ids || response.sheet_ids.length === 0) {
        throw new Error(response?.detail || "Upload succeeded but no sheet records were returned by the server.");
      }

      const sheetId = response.sheet_ids[0];
      const jobIds = response.job_ids || [];

      if (evalData) {
        sessionStorage.setItem('evaluationData', JSON.stringify(evalData));
      }

      setUploading(false);
      setFiles([]);
      navigate(`/review?sheetId=${sheetId}`, { 
        state: { 
          sheetId, 
          fileUrls: uploadedFileUrls,
          fileTypes: uploadedFileTypes,
          fileUrl: uploadedFileUrls.length > 0 ? uploadedFileUrls[0] : null, 
          fileType: uploadedFileTypes.length > 0 ? uploadedFileTypes[0] : null,
          evaluationData: evalData
        } 
      });
    } catch (error) {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      console.error('Upload failed:', error);
      setUploading(false);
      setErrorMessage(error.message || "Failed to upload and evaluate answer sheets. Please ensure backend is active.");
    }
  };

  return (
    <div className="upload-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>Upload Answer Sheets</h1>
          <p className="subtitle">Upload 1 to 50 scanned PDFs or images (JPG, PNG) for batch AI evaluation.</p>
        </div>
      </header>

      {errorMessage && (
        <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.5rem', borderColor: 'var(--error-color)', color: 'var(--error-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertCircle size={20} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Exam & Student Details Form */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', margin: 0 }}>Evaluation Metadata</h3>
          <span style={{ fontSize: '0.85rem', color: files.length >= 50 ? '#FF3535' : 'var(--accent-primary)', background: 'rgba(255,255,255,0.04)', padding: '0.3rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border-glass)', fontWeight: 600 }}>
            Batch Capacity: {files.length} / 50 Files Selected
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Exam ID:</label>
            <input 
              type="number" 
              min="1"
              step="1"
              value={examId} 
              onChange={(e) => {
                const val = e.target.value;
                if (val === '') {
                  setExamId('');
                } else {
                  const num = parseInt(val, 10);
                  setExamId(isNaN(num) || num < 1 ? '1' : num.toString());
                }
              }}
              onKeyDown={(e) => {
                if (e.key === '-' || e.key === 'e') {
                  e.preventDefault();
                }
              }}
              style={{
                width: '100%',
                padding: '0.6rem 0.8rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Student Roll Number Prefix:</label>
            <input 
              type="text" 
              value={studentRoll} 
              onChange={(e) => setStudentRoll(e.target.value)}
              placeholder="e.g. 2024CS001"
              style={{
                width: '100%',
                padding: '0.6rem 0.8rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)'
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Evaluation Mode:</label>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', padding: '0.6rem 0.8rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.9rem' }}>
              <input 
                type="checkbox" 
                checked={isMultiPage} 
                onChange={(e) => setIsMultiPage(e.target.checked)} 
                style={{ marginRight: '0.5rem', width: '16px', height: '16px', accentColor: 'var(--accent-primary)' }}
              />
              Stitch as single multi-page sheet
            </label>
          </div>
        </div>
      </div>

      <div className="upload-content">
        <div 
          className={`dropzone glass-panel ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="dropzone-content">
            <div className="upload-icon-wrapper">
              <UploadCloud size={48} className="upload-icon" />
            </div>
            <h3>Drag & Drop up to 50 files here</h3>
            <p className="text-muted">Accepted formats: PDF, JPG, PNG (Max 50 files per batch)</p>
            
            <div className="divider"><span>OR</span></div>
            
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <input 
                type="file" 
                id="file-upload" 
                multiple 
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden-input" 
                onChange={handleFileSelect}
              />
              <label htmlFor="file-upload" className="btn-secondary">
                Browse Files
              </label>

              <input 
                type="file" 
                id="folder-upload" 
                webkitdirectory="true"
                directory="true"
                className="hidden-input" 
                onChange={handleFileSelect}
              />
              <label htmlFor="folder-upload" className="btn-secondary">
                Browse Folder (Bulk)
              </label>

              <button type="button" onClick={load50SampleBatch} className="btn-secondary" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', border: '1px solid rgba(0, 242, 254, 0.4)', color: 'var(--accent-primary)' }}>
                <Zap size={16} /> Load 50 Sample Batch
              </button>
            </div>
          </div>
        </div>

        {uploading && (
          <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem', border: '1px solid var(--accent-primary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', alignItems: 'center' }}>
              <span style={{ fontWeight: 600, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Loader2 size={18} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
                Evaluating Batch Papers: {processedFileCount} of {files.length} Completed
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-primary)', fontWeight: 700 }}>
                {uploadProgress}%
              </span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${uploadProgress}%`, height: '100%', background: 'linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%)', transition: 'width 0.3s ease' }}></div>
            </div>
          </div>
        )}

        {files.length > 0 && (
          <div className="file-list glass-panel animate-fade-in delay-1">
            <div className="file-list-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0 }}>Batch Ready ({files.length} / 50 Files)</h3>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>All 50 sheets will be evaluated against rubric in parallel.</span>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button type="button" onClick={clearAllFiles} className="btn-secondary" style={{ padding: '0.6rem 1rem', fontSize: '0.85rem' }}>
                  Clear All
                </button>
                <button 
                  className="btn-primary" 
                  onClick={handleUpload}
                  disabled={uploading}
                >
                  {uploading ? `Processing (${processedFileCount}/${files.length})...` : `Start Batch Evaluation (${files.length} Papers)`}
                </button>
              </div>
            </div>
            
            <div className="files-grid" style={{ maxHeight: '400px', overflowY: 'auto', paddingRight: '0.5rem' }}>
              {files.map((file, idx) => (
                <div key={idx} className="file-item animate-fade-in" style={{ animationDelay: `${Math.min(idx, 20) * 0.03}s` }}>
                  <div className="file-info">
                    <div className="file-icon">
                      <File size={20} />
                    </div>
                    <div className="file-details">
                      <p className="file-name">{file.name}</p>
                      <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <button className="remove-btn" onClick={() => removeFile(idx)}>
                    <X size={18} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
