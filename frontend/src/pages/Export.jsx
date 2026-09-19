import { Download, FileDown, AlertCircle, CheckCircle, X, Loader2, Link, LayoutGrid, BookOpen } from 'lucide-react';
import { useState } from 'react';
import { AppApi } from '../api/client';
import './Dashboard.css';

const Export = () => {
  const [examId, setExamId] = useState('1');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);
  
  // LMS Sync state
  const [showLmsModal, setShowLmsModal] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [courseId, setCourseId] = useState('');
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);
    try {
      const response = await AppApi.exportExamResults(examId);

      // The backend returns a StreamingResponse (CSV),
      // but apiClient.get() uses response.json().
      // Since we need the raw blob for CSV download, we handle it specially.

      const blob = await fetch(`/api/v1/exams/${examId}/export`).then(r => r.blob());
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `exam_${examId}_results.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Export error:", err);
      setError("Failed to export grades. Ensure the backend is running and the exam ID is correct.");
    } finally {
      setIsExporting(false);
    }
  };

  const openLmsModal = (provider) => {
    setSelectedProvider(provider);
    setCourseId('');
    setSyncResult(null);
    setError(null);
    setShowLmsModal(true);
  };

  const closeLmsModal = () => {
    setShowLmsModal(false);
    setSelectedProvider(null);
    setSyncResult(null);
    setError(null);
  };

  const handleSyncLms = async () => {
    if (!courseId.trim()) {
      setError("Please enter a valid Course ID.");
      return;
    }
    
    setIsSyncing(true);
    setError(null);
    setSyncResult(null);
    
    try {
      const response = await AppApi.syncToLms(examId, selectedProvider, courseId);
      setSyncResult(response.message);
    } catch (err) {
      console.error("Sync error:", err);
      setError(err.message || "Failed to sync with LMS.");
    } finally {
      setIsSyncing(false);
    }
  };

  const lmsProviders = [
    { name: 'Canvas LMS', icon: <BookOpen size={24} />, color: '#E72429' },
    { name: 'Google Classroom', icon: <LayoutGrid size={24} />, color: '#139D59' },
    { name: 'Moodle', icon: <Link size={24} />, color: '#F98012' }
  ];

  return (
    <div className="dashboard-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>Sync & Export Grades</h1>
          <p className="subtitle">Sync results directly to your LMS or download them for your records.</p>
        </div>
      </header>

      <div style={{ maxWidth: '300px', marginBottom: '2rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Target Exam ID:</label>
        <input 
          type="number" 
          min="1"
          step="1"
          value={examId} 
          onChange={(e) => {
            const val = e.target.value;
            setExamId(val === '' ? '' : (parseInt(val, 10) || '1').toString());
          }}
          onKeyDown={(e) => {
            if (e.key === '-' || e.key === 'e') e.preventDefault();
          }}
          style={{ 
            width: '100%', padding: '0.75rem', borderRadius: '8px', 
            border: '1px solid var(--border-color)', background: 'var(--bg-primary)', 
            color: 'var(--text-primary)'
          }}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
        {/* LMS Sync Section */}
        <section className="glass-panel" style={{ padding: '2rem' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Link size={20} /> Direct LMS Sync
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Automatically push graded exam scores directly to your learning management system.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {lmsProviders.map((provider) => (
              <button 
                key={provider.name}
                className="glass-panel"
                style={{ 
                  display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', 
                  border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.03)',
                  cursor: 'pointer', transition: 'all 0.2s', textAlign: 'left'
                }}
                onClick={() => openLmsModal(provider.name)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = provider.color;
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div style={{ color: provider.color }}>{provider.icon}</div>
                <div style={{ flex: 1, fontWeight: 500 }}>Sync to {provider.name}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Manual Export Section */}
        <section className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileDown size={20} /> Manual Data Export
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Download a standard CSV file containing student roll numbers, scores, and review statuses for manual import.
          </p>
          
          <div style={{ marginTop: 'auto', textAlign: 'center', padding: '2rem 0' }}>
            <FileDown size={48} className="text-secondary" style={{ margin: '0 auto 1.5rem auto', opacity: 0.5 }} />
            <button 
              className="btn-primary" 
              onClick={handleExport} 
              disabled={isExporting}
              style={{ width: '100%', maxWidth: '250px' }}
            >
              {isExporting ? <><Loader2 size={18} className="animate-spin" /> Exporting...</> : <><Download size={18} /> Download CSV</>}
            </button>
          </div>
        </section>
      </div>

      {/* Error display for manual export if needed outside modal */}
      {error && !showLmsModal && (
        <div style={{ color: 'var(--error-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', marginTop: '1rem' }}>
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* LMS Sync Modal */}
      {showLmsModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: '450px', padding: '2rem', position: 'relative' }}>
            <button 
              onClick={closeLmsModal}
              style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>
            
            <h2 style={{ fontSize: '1.4rem', marginBottom: '0.5rem' }}>Connect to {selectedProvider}</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '2rem' }}>
              Syncing grades for Exam ID: <strong>{examId}</strong>
            </p>

            {syncResult ? (
              <div style={{ textAlign: 'center', padding: '2rem 0' }}>
                <CheckCircle size={48} className="text-success" style={{ margin: '0 auto 1rem auto' }} />
                <p style={{ fontSize: '1.1rem', color: 'var(--success-color)' }}>{syncResult}</p>
                <button className="btn-secondary" onClick={closeLmsModal} style={{ marginTop: '2rem', width: '100%' }}>Close</button>
              </div>
            ) : (
              <div>
                <div style={{ marginBottom: '1.5rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-primary)', fontSize: '0.9rem' }}>{selectedProvider} Course ID *</label>
                  <input 
                    type="text" 
                    value={courseId}
                    onChange={(e) => setCourseId(e.target.value)}
                    placeholder="e.g. 1048293"
                    style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}
                  />
                </div>
                
                {error && (
                  <div style={{ color: 'var(--error-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', marginBottom: '1rem' }}>
                    <AlertCircle size={16} /> {error}
                  </div>
                )}

                <button 
                  className="btn-primary" 
                  onClick={handleSyncLms} 
                  disabled={isSyncing}
                  style={{ width: '100%' }}
                >
                  {isSyncing ? <><Loader2 size={18} className="animate-spin" /> Syncing Grades...</> : 'Sync Now'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Export;
