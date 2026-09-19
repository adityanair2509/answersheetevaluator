import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { FileText, Award, AlertCircle, Eye, Search, ArrowUpRight, Download } from 'lucide-react';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import './Dashboard.css';

const MyResults = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedResult, setSelectedResult] = useState(null);
  const [showReevalModal, setShowReevalModal] = useState(false);
  const [reevalReason, setReevalReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [results, setResults] = useState([]);

  useEffect(() => {
    import('../api/client').then(({ AppApi }) => {
      AppApi.getMyResults().then(data => {
        if (data && data.length > 0) {
          setResults(data);
        }
      });
    });
  }, []);

  const filteredResults = results.filter(r => 
    r.subject.toLowerCase().includes(searchTerm.toLowerCase()) || 
    r.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleReevalSubmit = async (e) => {
    e.preventDefault();
    if (!reevalReason.trim()) return;
    
    setIsSubmitting(true);
    try {
      const { AppApi } = await import('../api/client');
      await AppApi.requestReevaluation(selectedResult.rawId || selectedResult.id, reevalReason);
      
      // Update local state to reflect 'Under Review'
      setResults(prev => prev.map(r => r.id === selectedResult.id ? { ...r, status: 'Under Review' } : r));
      setSelectedResult(prev => ({ ...prev, status: 'Under Review' }));
      
      alert(`Re-evaluation requested for ${selectedResult.id}. It has been sent to your teacher.`);
      setShowReevalModal(false);
      setReevalReason('');
    } catch (err) {
      console.error(err);
      alert("Failed to submit request.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const generatePDF = (result) => {
    try {
      const doc = new jsPDF();
      
      // Header
      doc.setFontSize(22);
      doc.setTextColor(255, 51, 51); // ScribScore red
      doc.text('ScribScore', 14, 20);
      
      doc.setFontSize(14);
      doc.setTextColor(100);
      doc.text('Official Result Report', 14, 28);
      
      // Details
      doc.setFontSize(11);
      doc.setTextColor(40);
      doc.text(`Student ID: ST-2023-992`, 14, 45);
      doc.text(`Test ID: ${result.id}`, 14, 52);
      doc.text(`Subject: ${result.subject}`, 14, 59);
      doc.text(`Date of Test: ${result.date}`, 14, 66);
      doc.text(`Status: ${result.status}`, 14, 73);

      // Score Table
      const tableBody = [
        ['Score Obtained', `${result.score} out of ${result.total}`],
        ['Percentage', `${Math.round((result.score / result.total) * 100)}%`],
      ];
      if (result.rank != null) tableBody.push(['Class Rank', `#${result.rank}`]);
      if (result.percentile != null) tableBody.push(['Percentile', `${result.percentile}th`]);

      autoTable(doc, {
        startY: 85,
        head: [['Metric', 'Value']],
        body: tableBody,
        headStyles: { fillColor: [255, 51, 51] },
        theme: 'grid',
      });

      // Footer
      const finalY = doc.lastAutoTable ? doc.lastAutoTable.finalY : 120;
      doc.setFontSize(9);
      doc.setTextColor(150);
      doc.text(`Generated automatically by ScribScore on ${new Date().toLocaleDateString()}`, 14, finalY + 20);

      // Download
      doc.save(`Result_${result.subject.replace(/\s+/g, '_')}_${result.id}.pdf`);
    } catch (error) {
      console.error("PDF generation failed:", error);
      alert("Failed to generate PDF. Check console for details.");
    }
  };

  return (
    <div className="dashboard-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>My Results</h1>
          <p className="subtitle">View your past evaluations, percentiles, and request re-checks.</p>
        </div>
      </header>

      <div style={{ marginBottom: '20px', position: 'relative', maxWidth: '400px' }}>
        <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input 
          type="text" 
          placeholder="Search by subject or test ID..." 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '10px 10px 10px 38px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
            background: 'var(--surface-color)',
            color: 'var(--text-primary)',
            outline: 'none'
          }}
        />
      </div>

      <div className="table-responsive glass-panel animate-fade-in delay-1">
        <table className="activity-table">
          <thead>
            <tr>
              <th>Test ID</th>
              <th>Subject</th>
              <th>Date</th>
              <th>Score</th>
              <th>Class Standing</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredResults.map((result, idx) => (
              <tr key={result.id} style={{ animationDelay: `${0.2 + idx * 0.1}s` }} className="animate-fade-in">
                <td className="font-mono">{result.id}</td>
                <td className="font-semibold">{result.subject}</td>
                <td className="text-muted">{result.date}</td>
                <td style={{ fontWeight: 'bold' }}>
                  {result.score !== null ? (
                    <span style={{ color: result.score >= 90 ? 'var(--success-color)' : 'inherit' }}>
                      {result.score}/{result.total}
                    </span>
                  ) : '-'}
                </td>
                <td>
                  {result.rank != null ? (
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span>Rank: #{result.rank}</span>
                      {result.percentile != null && <span className="text-muted" style={{ fontSize: '0.8rem' }}>Top {100 - result.percentile}%</span>}
                    </div>
                  ) : <span className="text-muted">N/A</span>}
                </td>
                <td>
                  <span className={`badge badge-status-${result.status.toLowerCase().replace(' ', '-')}`}>
                    {result.status}
                  </span>
                </td>
                <td>
                  <button 
                    className="btn-secondary" 
                    style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                    onClick={() => setSelectedResult(result)}
                    disabled={result.status !== 'Graded' && result.status !== 'Evaluated'}
                  >
                    <Eye size={14} style={{ marginRight: '6px' }} />
                    View Details
                  </button>
                </td>
              </tr>
            ))}
            {filteredResults.length === 0 && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '30px' }} className="text-muted">
                  No results found matching your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Details Modal */}
      {selectedResult && !showReevalModal && createPortal(
        <div className="modal-overlay" onClick={() => setSelectedResult(null)}>
          <div className="modal-content glass-panel" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', width: '90%' }}>
            <div className="modal-header">
              <h2>{selectedResult.subject} - Details</h2>
              <button className="close-btn" onClick={() => setSelectedResult(null)}>×</button>
            </div>
            <div className="modal-body" style={{ display: 'flex', gap: '20px', flexDirection: 'column' }}>
              
              <div style={{ display: 'flex', gap: '20px' }}>
                {/* Stats Summary */}
                <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                  <div className="stat-card" style={{ background: 'var(--bg-primary)', padding: '15px' }}>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>Final Score</p>
                    <h3 style={{ fontSize: '1.75rem', color: 'var(--accent-primary)', whiteSpace: 'nowrap' }}>{selectedResult.score}/{selectedResult.total}</h3>
                  </div>
                  <div className="stat-card" style={{ background: 'var(--bg-primary)', padding: '15px' }}>
                    <p className="text-muted" style={{ fontSize: '0.9rem' }}>Percentile</p>
                    <h3 style={{ fontSize: '1.75rem', whiteSpace: 'nowrap' }}>{selectedResult.percentile != null ? `${selectedResult.percentile}th` : 'N/A'}</h3>
                  </div>
                  <div className="stat-card" style={{ gridColumn: '1 / -1', background: 'var(--bg-primary)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <p className="text-muted">Class Rank</p>
                        <h3>{selectedResult.rank != null ? `#${selectedResult.rank}` : 'N/A'}</h3>
                      </div>
                      <Award size={32} style={{ color: 'var(--warning-color)' }} />
                    </div>
                  </div>
                </div>

                {/* Simulated PDF Viewer */}
                <div style={{ flex: 2, background: 'var(--bg-primary)', borderRadius: '12px', padding: '15px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
                  <h4 style={{ marginBottom: '10px' }}>Checked Answer Sheet</h4>
                  <div style={{ flex: 1, background: '#e2e8f0', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', minHeight: '200px' }}>
                    <div style={{ textAlign: 'center' }}>
                      <FileText size={48} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
                      <p style={{ color: 'black' }}>Sheet_{selectedResult.id}_scanned.pdf</p>
                      <button className="btn-secondary" style={{ marginTop: '15px', background: 'white', color: '#0f172a', borderColor: '#cbd5e1' }}>
                        <ArrowUpRight size={16} /> Open Full PDF
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', borderTop: '1px solid var(--border-glass)', paddingTop: '15px' }}>
                <button 
                  className="btn-secondary" 
                  onClick={() => generatePDF(selectedResult)}
                  style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  <Download size={16} />
                  Download Result (PDF)
                </button>
                <button 
                  className="btn-secondary" 
                  style={{ color: 'var(--error-color)', borderColor: 'var(--error-color)' }}
                  onClick={() => setShowReevalModal(true)}
                  disabled={selectedResult.status === 'Under Review'}
                >
                  <AlertCircle size={16} style={{ marginRight: '8px' }} />
                  {selectedResult.status === 'Under Review' ? 'Already Requested' : 'Request Re-evaluation'}
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Re-evaluation Modal */}
      {showReevalModal && createPortal(
        <div className="modal-overlay" onClick={() => setShowReevalModal(false)}>
          <div className="modal-content glass-panel" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Request Re-evaluation</h2>
              <button className="close-btn" onClick={() => setShowReevalModal(false)}>×</button>
            </div>
            <form onSubmit={handleReevalSubmit}>
              <div className="modal-body">
                <p style={{ marginBottom: '15px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  If you believe a question was graded incorrectly for <strong>{selectedResult.subject}</strong>, please provide the details below.
                </p>
                <div className="form-group" style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '8px' }}>Reason for Re-evaluation</label>
                  <textarea 
                    required
                    rows="4"
                    value={reevalReason}
                    onChange={(e) => setReevalReason(e.target.value)}
                    placeholder="E.g., Question 4 was marked wrong but my answer matches the key..."
                    style={{
                      width: '100%',
                      padding: '10px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      resize: 'vertical'
                    }}
                  />
                </div>
              </div>
              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', padding: '15px', borderTop: '1px solid var(--border-glass)' }}>
                <button type="button" className="btn-secondary" onClick={() => setShowReevalModal(false)} disabled={isSubmitting}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={isSubmitting}>{isSubmitting ? 'Submitting...' : 'Submit Request'}</button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      <style>{`
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          animation: fadeIn 0.2s ease-out forwards;
        }
        .modal-content {
          width: 90%;
          max-width: 500px;
          border-radius: 16px;
          overflow-y: auto;
          max-height: 90vh;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
          animation: slideUp 0.3s ease-out forwards;
        }
        .modal-header {
          padding: 20px;
          border-bottom: 1px solid var(--border-glass);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .modal-header h2 { margin: 0; font-size: 1.25rem; }
        .close-btn {
          background: none; border: none; color: var(--text-muted); font-size: 1.5rem;
          cursor: pointer; padding: 0; line-height: 1;
        }
        .close-btn:hover { color: var(--text-primary); }
        .modal-body { padding: 20px; }
      `}</style>
    </div>
  );
};

export default MyResults;
