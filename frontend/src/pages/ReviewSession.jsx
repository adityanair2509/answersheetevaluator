import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ZoomIn, ZoomOut, Check, X, AlertTriangle, BookOpen, Brain, Image as ImageIcon, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { AppApi } from '../api/client';
import './ReviewSession.css';

const ReviewSession = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [reviewData, setReviewData] = useState(null);
  const [score, setScore] = useState('');
  const [maxScore, setMaxScore] = useState(10);
  const [zoom, setZoom] = useState(100);
  const [statusMsg, setStatusMsg] = useState(null);
  const [reviewStatus, setReviewStatus] = useState('NEEDS_REVIEW');
  const [loading, setLoading] = useState(true);
  const [actualSheetId, setActualSheetId] = useState(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);


  const fileUrls = useMemo(() => {
    if (reviewData?.fileUrls && reviewData.fileUrls.length > 0) {
      return reviewData.fileUrls;
    }
    return location.state?.fileUrls || (sessionStorage.getItem('previewFileUrls') ? JSON.parse(sessionStorage.getItem('previewFileUrls')) : [location.state?.fileUrl || sessionStorage.getItem('previewFileUrl')].filter(Boolean));
  }, [location.state, reviewData]);

  const fileTypes = useMemo(() => {
    if (reviewData?.fileTypes && reviewData.fileTypes.length > 0) {
      return reviewData.fileTypes;
    }
    return location.state?.fileTypes || (sessionStorage.getItem('previewFileTypes') ? JSON.parse(sessionStorage.getItem('previewFileTypes')) : [location.state?.fileType || sessionStorage.getItem('previewFileType')].filter(Boolean));
  }, [location.state, reviewData]);

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const querySheetId = searchParams.get('sheetId');
    const idToFetch = querySheetId || location.state?.sheetId || 'next';

    setLoading(true);
    AppApi.getSheetReview(idToFetch)
      .then((data) => {
        if (data && (data.evaluations && data.evaluations.length > 0 || data.studentRoll)) {
          setReviewData(data);

          if (data.evaluations && data.evaluations.length > 0) {
            const firstEval = data.evaluations[0];
            setScore(firstEval.score !== undefined ? firstEval.score : 0);
            setMaxScore(firstEval.maxScore || 10);
            setReviewStatus(firstEval.reviewStatus || 'NEEDS_REVIEW');
          }
          setActualSheetId(data.sheetId);
        } else {
          setReviewData(null);
        }
      })
      .catch((err) => {
        console.warn("Could not fetch sheet review from backend:", err);
        setReviewData(null);
      })
      .finally(() => setLoading(false));
  }, [location.search, location.state]);

  // Derived state for the currently selected question
  const currentEval = useMemo(() => {
    if (!reviewData?.evaluations || reviewData.evaluations.length === 0) return null;
    return reviewData.evaluations[currentQuestionIndex] || reviewData.evaluations[0];
  }, [reviewData, currentQuestionIndex]);

  const studentAnswer = currentEval ? (currentEval.rawText || 'No text extracted from this page.') : (loading ? 'Loading extracted text...' : 'No answer sheet waiting for review.');
  const expectedAnswer = currentEval ? (currentEval.expectedAnswer || currentEval.expected_answer || currentEval.rubric || 'No expected answer available.') : (loading ? 'Loading rubric...' : 'No rubric available.');
  const llmRationale = currentEval ? (currentEval.llmRationale || currentEval.reasoning) : (loading ? 'Analyzing...' : 'No rationale available.');
  const aiConfidence = currentEval ? currentEval.aiConfidence : 0;
  const missingConcepts = currentEval ? currentEval.missingConcepts : [];


  const getFullFileUrl = (url) => {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    return import.meta.env.DEV ? `http://localhost:8000${url}` : url;
  };

  const handleApprove = async () => {
    setStatusMsg(null);
    const numScore = parseFloat(score);
    if (isNaN(numScore) || numScore < 0 || numScore > maxScore) {
      setStatusMsg({ type: 'error', text: `Please enter a valid score between 0 and ${maxScore}.` });
      return;
    }

    try {
      if (actualSheetId && currentEval) {
        await AppApi.approveScore(actualSheetId, numScore, "teacher1", currentEval.questionNumber);
      }
      setReviewStatus('APPROVED');
      setStatusMsg({ type: 'success', text: `Score of ${numScore}/${maxScore} for Q${currentEval?.questionNumber || 1} successfully approved!` });
    } catch (err) {
      console.error("Approve score error:", err);
      setStatusMsg({ type: 'error', text: `Failed to approve score: ${err.message}` });
    }
  };

  const handleFlag = async () => {
    setStatusMsg(null);
    try {
      if (actualSheetId && currentEval) {
        await AppApi.flagIssue(actualSheetId, "Flagged for manual review by teacher", currentEval.questionNumber);
      }
      setReviewStatus('FLAGGED');
      setStatusMsg({ type: 'warning', text: `Question ${currentEval?.questionNumber || 1} flagged successfully!` });
    } catch (err) {
      console.error("Flag issue error:", err);
      setStatusMsg({ type: 'error', text: `Failed to flag issue: ${err.message}` });
    }
  };

  const getStatusBadge = () => {
    if (reviewStatus === 'APPROVED' || reviewStatus === 'AUTO_APPROVED' || reviewStatus === 'REVIEWED') {
      return <span className="badge badge-success">Approved</span>;
    }
    if (reviewStatus === 'FLAGGED') {
      return <span className="badge badge-danger">Flagged</span>;
    }
    return <span className="badge badge-warning">Needs Review</span>;
  };

  return (
    <div className="review-container animate-fade-in">
      {/* Fallback Mode Warning Banner */}
      {!loading && reviewData && currentEval?.aiConfidence === 78 && (
        <div style={{
          backgroundColor: 'rgba(255, 165, 0, 0.15)',
          border: '1px solid var(--warning-color)',
          color: 'var(--warning-color)',
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.9rem',
          fontWeight: 500
        }}>
          <AlertTriangle size={18} />
          <span><strong>Local Extraction Mode:</strong> No active Gemini API key detected. This result was generated using local fallback OCR. Manual verification is strongly recommended.</span>
        </div>
      )}

      <header className="review-header">
        <div className="review-title">
          <button className="badge badge-neutral">
            {reviewData?.studentRoll ? `Roll: ${reviewData.studentRoll} (Sheet #${reviewData.sheetId})` : (loading ? 'Loading...' : 'Queue Empty')}
          </button>
          <h1 style={{ margin: '0.5rem 0' }}>Reviewing Answer Sheet</h1>

          {reviewData?.evaluations && reviewData.evaluations.length > 1 && (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Question:</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                {reviewData.evaluations.map((_, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setCurrentQuestionIndex(idx);
                      setScore(reviewData.evaluations[idx].score);
                      setMaxScore(reviewData.evaluations[idx].maxScore);
                      setReviewStatus(reviewData.evaluations[idx].reviewStatus);
                    }}
                    className={`btn-secondary` + (currentQuestionIndex === idx ? ' active-question' : '')}
                    style={{
                      padding: '2px 8px',
                      fontSize: '0.75rem',
                      background: currentQuestionIndex === idx ? 'var(--accent-primary)' : 'transparent',
                      color: currentQuestionIndex === idx ? '#000' : 'var(--text-primary)',
                      border: '1px solid var(--border-color)'
                    }}
                  >
                    {reviewData.evaluations[idx].questionNumber}
                  </button>
                ))}
              </div>
            </div>
          )}
          {getStatusBadge()}
        </div>
        <div className="review-actions">
          <button className="btn-secondary text-danger" onClick={handleFlag}>
            <X size={18} /> Flag Issue
          </button>
          <button className="btn-primary" onClick={handleApprove}>
            <Check size={18} /> Approve Score
          </button>
        </div>
      </header>

      {statusMsg && (
        <div className="glass-panel animate-fade-in" style={{
          padding: '1rem',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          borderColor: statusMsg.type === 'success' ? 'var(--success-color)' : (statusMsg.type === 'warning' ? 'var(--warning-color)' : 'var(--error-color)'),
          color: statusMsg.type === 'success' ? 'var(--success-color)' : (statusMsg.type === 'warning' ? 'var(--warning-color)' : 'var(--error-color)')
        }}>
          {statusMsg.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          <span style={{ fontWeight: 500 }}>{statusMsg.text}</span>
        </div>
      )}

      <div className="review-workspace">
        {/* Left Pane - Image Viewer */}
        <div className="workspace-pane image-pane glass-panel">
          <div className="pane-header">
            <div className="pane-title">
              <ImageIcon size={18} /> Scanned Document Preview
            </div>
            <div className="image-controls">
              <button className="icon-btn" onClick={() => setZoom(Math.max(50, zoom - 10))}><ZoomOut size={16} /></button>
              <span className="zoom-level">{zoom}%</span>
              <button className="icon-btn" onClick={() => setZoom(Math.min(200, zoom + 10))}><ZoomIn size={16} /></button>
            </div>
          </div>

          <div className="image-viewer" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto' }}>
              {fileUrls && fileUrls.length > 0 ? (
                fileUrls.map((url, idx) => {
                  const fullUrl = getFullFileUrl(url);
                  return (
                  <div key={idx} className="mock-document" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                    {fileTypes[idx] === 'application/pdf' ? (
                      <div style={{ width: '100%', height: '100%', minHeight: '600px', position: 'relative' }}>
                        <iframe
                          src={`${fullUrl}#toolbar=0`}
                          style={{ width: '100%', height: '600px', border: 'none', borderRadius: '4px' }}
                          title={`Page ${idx + 1}`}
                        />
                        <div style={{
                          position: 'absolute', top: '10px', right: '10px',
                          zIndex: 10
                        }}>
                          <a
                            href={fullUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-secondary"
                            style={{ fontSize: '0.7rem', padding: '4px 8px' }}
                          >
                            Open Full PDF ↗
                          </a>
                        </div>
                      </div>
                    ) : (
                      <>
                        <img
                          src={fullUrl}
                          alt={`Uploaded sheet page ${idx + 1}`}
                          style={{ width: `${zoom}%`, height: 'auto', objectFit: 'contain' }}
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextElementSibling.style.display = 'block';
                          }}
                        />
                        <div style={{ display: 'none', padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                          <ImageIcon size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
                          <h4>Document Not Available</h4>
                          <p>Unable to load document from the server.</p>
                        </div>
                      </>
                    )}
                  </div>
                )})
              ) : (
              <div className="mock-document">
                <div className="mock-handwriting">
                  <p>Q1. Quadratic Factorization</p>
                  <p className="cursive">2x² - x - 6 = 0</p>
                  <p className="cursive">2x² - 4x + 3x - 6 = 0</p>
                  <p className="cursive">2x(x - 2) + 3(x - 2) = 0</p>
                  <p className="cursive">(2x + 3)(x - 2) = 0</p>
                  <p className="cursive">x = -3/2, x = 2</p>
                </div>
                <div className="bounding-box pulse-box"></div>
              </div>
            )}
          </div>
        </div>

        {/* Right Pane - AI Evaluation */}
        <div className="workspace-pane data-pane">
          <div className="data-section glass-panel animate-fade-in delay-1">
            <div className="section-title">
              <BookOpen size={18} className="text-accent" /> Extracted Text (OCR)
            </div>
            <div className="text-content" style={{ whiteSpace: 'pre-line' }}>
              {studentAnswer}
            </div>
          </div>

          <div className="data-section glass-panel animate-fade-in delay-2">
            <div className="section-title">
              <AlertTriangle size={18} className="text-warning" /> Ground Truth Expected Answer (Rubric)
            </div>
            <div className="text-content expected">
              {expectedAnswer}
            </div>
          </div>

          <div className="data-section glass-panel highlight-section animate-fade-in delay-3">
            <div className="section-title">
              <Brain size={18} className="text-purple" /> AI Evaluation & Rationale
            </div>

            <div className="evaluation-content">
              <p className="rationale">"{llmRationale}"</p>

              {missingConcepts && missingConcepts.length > 0 && (
                <div style={{ marginTop: '0.75rem', marginBottom: '0.75rem', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,165,0,0.1)', border: '1px solid rgba(255,165,0,0.3)' }}>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--warning-color)', fontWeight: 600 }}>Missing Concepts / Feedback:</p>
                  <ul style={{ margin: '0.25rem 0 0 1.2rem', padding: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {missingConcepts.map((item, i) => <li key={i}>{item}</li>)}
                  </ul>
                </div>
              )}

              <div className="scoring-widget">
                <div className="score-control">
                  <label>Adjust Score (Out of {maxScore})</label>
                  <div className="score-input-group">
                    <input
                      type="number"
                      value={score}
                      onChange={(e) => setScore(e.target.value)}
                      step="0.5"
                      min="0"
                      max={maxScore}
                      className="score-input"
                    />
                    <span className="max-score">/ {maxScore}</span>
                  </div>
                </div>

                <div className="confidence-meter">
                  <div className="meter-label">
                    <span>AI Confidence</span>
                    <span className={aiConfidence >= 85 ? "text-success" : "text-warning"}>{aiConfidence}%</span>
                  </div>
                  <div className="meter-bar">
                    <div className={`meter-fill ${aiConfidence >= 85 ? "success" : "warning"}`} style={{ width: `${aiConfidence}%`, background: aiConfidence >= 85 ? 'var(--success-color)' : '' }}></div>
                  </div>
                  <p className="meter-help">
                    {aiConfidence >= 85
                      ? "High confidence score. High agreement with rubric."
                      : "Medium confidence score. Manual teacher review recommended."}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewSession;
