import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, FileText, Search, Filter, Download, ExternalLink } from 'lucide-react';
import { AppApi } from '../api/client';
import './Dashboard.css'; // Reusing dashboard styles for consistency

const GradedSheets = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const statusFilter = location.state?.status || 'ALL';

  const [sheets, setSheets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchSheets = async () => {
      setLoading(true);
      try {
        const data = await AppApi.getGradedSheets(statusFilter);
        setSheets(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSheets();
  }, [statusFilter]);

  const filteredSheets = sheets.filter(s => {
    const term = searchTerm.toLowerCase();
    return (
      (s.studentRoll || '').toLowerCase().includes(term) ||
      (s.studentName || '').toLowerCase().includes(term) ||
      (s.examName || '').toLowerCase().includes(term)
    );
  });

  const handleRowClick = (sheetId) => {
    navigate(`/review?sheetId=${sheetId}`);
  };

  return (
    <div className="dashboard-container animate-fade-in">
      <header className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn-secondary" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={18} /> Back to Dashboard
          </button>
          <h1>
            {statusFilter === 'AUTO_APPROVED' ? 'Auto-Approved Sheets' : 'All Graded Sheets'}
          </h1>
        </div >
      </header>

      <div className="glass-panel animate-fade-in delay-1" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
            <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
              <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
              <input
                type="text"
                placeholder="Search students, exams..."
                className="input-field"
                style={{ paddingLeft: '40px' }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <button className="btn-secondary">
            <Download size={18} /> Export CSV
          </button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
            <div className="loader-spin" style={{ marginBottom: '1rem' }}></div>
            <p>Loading graded sheets...</p>
          </div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--danger)' }}>
            <p>Error loading data: {error}</p>
            <button className="btn-primary" style={{ marginTop: '1rem' }} onClick={() => window.location.reload()}>Retry</button>
          </div>
        ) : filteredSheets.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
            <FileText size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <p>No graded sheets found for the current filter.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="activity-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Roll</th>
                  <th>Exam</th>
                  <th>Marks</th>
                  <th>%</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredSheets.map((s) => (
                  <tr key={s.sheetId} onClick={() => handleRowClick(s.sheetId)} style={{ cursor: 'pointer' }} className="animate-fade-in">
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span className="font-semibold">{s.studentName || 'N/A'}</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>{s.evaluationDate || 'N/A'}</span>
                      </div>
                    </td>
                    <td className="font-mono">{s.studentRoll || 'N/A'}</td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span>{s.examName || 'N/A'}</span>
                        <span className="text-muted" style={{ fontSize: '0.75rem' }}>ID: {s.examId || 'N/A'}</span>
                      </div>
                    </td>
                    <td>{s.obtainedMarks ?? 0} / {s.totalMarks ?? 0}</td>
                    <td className="font-semibold">{s.percentage ?? 0}%</td>
                    <td>
                      <span className={`badge ${s.confidence >= 85 ? 'badge-success' : 'badge-warning'}`}>
                        {s.confidence ?? 0}%
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-status-${(s.reviewStatus || 'UNKNOWN').toLowerCase()}`}>
                        {s.reviewStatus || 'UNKNOWN'}
                      </span>
                    </td>
                    <td>
                      <button className="btn-secondary" style={{ padding: '4px 8px' }}>
                        Review <ExternalLink size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default GradedSheets;
