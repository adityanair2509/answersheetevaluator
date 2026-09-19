import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, AlertCircle, CheckCircle2, TrendingUp, X, Users, BookOpen, ThumbsDown, Plus, Check } from 'lucide-react';
import { AppApi } from '../api/client';
import ThemeToggle from '../components/ThemeToggle';
import './Dashboard.css';

const StatCard = ({ title, value, icon: Icon, colorClass, delay, onClick }) => (
  <div
    className={`stat-card glass-panel animate-fade-in ${delay} card-hover`}
    style={{ cursor: onClick ? 'pointer' : 'default' }}
    onClick={onClick}
  >
    <div className="stat-header">
      <div className={`stat-icon-wrapper ${colorClass}`}>
        <Icon size={24} />
      </div>
    </div>
    <div className="stat-body">
      <h3>{value}</h3>
      <p>{title}</p>
    </div>
  </div>
);

const PieChartCard = ({ title, value, percentage, delay, onClick }) => (
  <div 
    className={`stat-card glass-panel animate-fade-in ${delay} card-hover`} 
    style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', cursor: 'pointer' }}
    onClick={onClick}
  >
    <div className="stat-body" style={{ flex: 1 }}>
      <h3>{value}</h3>
      <p>{title}</p>
    </div>
    <div 
      className="pie-chart" 
      style={{
        width: '72px',
        height: '72px',
        borderRadius: '50%',
        border: '1px solid var(--border-color)',
        background: `conic-gradient(var(--accent-primary) ${Math.min(100, Math.max(0, percentage))}% , rgba(255, 255, 255, 0.1) 0)`,
        boxShadow: '0 8px 16px var(--border-glass)',
        transition: 'transform var(--transition-normal)'
      }}
    />
  </div>
);

const Dashboard = () => {
  const [chartModalOpen, setChartModalOpen] = useState(false);
  const [rubricModalOpen, setRubricModalOpen] = useState(false);
  const navigate = useNavigate();

  const [batches, setBatches] = useState([]);
  const [stats, setStats] = useState({
    totalGraded: 0,
    autoApproved: 0,
    needsReview: 0,
    averageScore: 0
  });

  // Answer Key Rubric state
  const [questions, setQuestions] = useState([]);
  const [qNumber, setQNumber] = useState(1);
  const [qText, setQText] = useState("Explain the difference between BFS and DFS graph traversal algorithms.");
  const [expectedAns, setExpectedAns] = useState("BFS uses a Queue (FIFO) and explores level-by-level. DFS uses a Stack (LIFO) or recursion to explore deep paths before backtracking.");
  const [maxMarks, setMaxMarks] = useState(10.0);
  const [rubricMessage, setRubricMessage] = useState(null);

  const [reevalRequests, setReevalRequests] = useState([]);

  const loadData = () => {
    AppApi.getRecentBatches().then(data => {
      if (Array.isArray(data)) setBatches(data);
    });
    
    AppApi.getDashboardStats().then(data => {
      if (data) setStats(data);
    });

    AppApi.getExamQuestions(1).then(data => {
      if (Array.isArray(data)) setQuestions(data);
    });

    AppApi.getReevaluations().then(data => {
      if (Array.isArray(data)) setReevalRequests(data);
    });
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveRubric = async (e) => {
    e.preventDefault();
    setRubricMessage(null);
    try {
      await AppApi.addExamQuestion(1, {
        question_number: parseInt(qNumber, 10),
        question_text: qText,
        expected_answer: expectedAns,
        max_marks: parseFloat(maxMarks),
        rubric_hints: "Ground truth expected answer for AI grading."
      });
      setRubricMessage("Answer Key & Rubric item saved to SQLite database successfully!");
      loadData();
    } catch (err) {
      console.error("Save rubric error:", err);
      setRubricMessage("Failed to save rubric item.");
    }
  };

  return (
    <div className="dashboard-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>Welcome back, Evaluator</h1>
          <p className="subtitle">Automated Answer Sheet Evaluation & Analytics System</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <ThemeToggle />
          <button className="btn-secondary" onClick={() => setRubricModalOpen(!rubricModalOpen)}>
            <BookOpen size={18} />
            Define Answer Key
          </button>
          <button className="btn-primary" onClick={() => navigate('/upload')}>
            <FileText size={18} />
            New Evaluation Batch
          </button>
        </div>
      </header>

      {/* Answer Key / Rubric Modal / Section */}
      {rubricModalOpen && (
        <div className="glass-panel animate-fade-in" style={{ padding: '1.5rem', marginBottom: '2rem', borderColor: 'var(--accent-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BookOpen size={20} className="text-accent" /> Define Exam Answer Key & Rubric (Exam ID #1)
            </h2>
            <button className="icon-btn" onClick={() => setRubricModalOpen(false)}><X size={18} /></button>
          </div>

          {/* Fallback Warning for Rubric Setup */}
          <div style={{
            backgroundColor: 'rgba(255, 165, 0, 0.1)',
            border: '1px solid var(--warning-color)',
            padding: '0.75rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            color: 'var(--warning-color)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertCircle size={16} />
            <span>Note: Without a configured Gemini API key, the system uses local fallback OCR.</span>
          </div>

          {rubricMessage && (
            <div style={{ color: 'var(--success-color)', marginBottom: '1rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Check size={16} /> {rubricMessage}
            </div>
          )}


          <form onSubmit={handleSaveRubric} style={{ display: 'grid', gap: '1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.3rem' }}>Question #:</label>
                <input 
                  type="number" 
                  value={qNumber} 
                  onChange={(e) => setQNumber(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} 
                  required 
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.3rem' }}>Question Text:</label>
                <input 
                  type="text" 
                  value={qText} 
                  onChange={(e) => setQText(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} 
                  required 
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.3rem' }}>Max Marks:</label>
                <input 
                  type="number" 
                  value={maxMarks} 
                  onChange={(e) => setMaxMarks(e.target.value)}
                  step="0.5"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} 
                  required 
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.3rem' }}>Ground Truth Expected Answer (Used by Gemini AI):</label>
              <textarea 
                rows="3"
                value={expectedAns} 
                onChange={(e) => setExpectedAns(e.target.value)}
                placeholder="Enter exact expected solution or rubric answer..."
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} 
                required 
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn-primary" style={{ width: 'auto' }}>
                <Plus size={16} /> Save Rubric Item
              </button>
            </div>
          </form>

          {questions.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Configured Rubric Items ({questions.length})</h3>
              <div className="table-responsive">
                <table className="activity-table">
                  <thead>
                    <tr>
                      <th>Q#</th>
                      <th>Question</th>
                      <th>Expected Answer</th>
                      <th>Max Marks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {questions.map((q) => (
                      <tr key={q.id}>
                        <td className="font-mono">Q{q.questionNumber}</td>
                        <td className="font-semibold">{q.questionText}</td>
                        <td className="text-muted" style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{q.expectedAnswer}</td>
                        <td>{q.maxMarks}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Database-Backed Metrics */}
      <section className="stats-grid">
        <StatCard
          title="Total Graded Sheets"
          value={stats.totalGraded.toLocaleString()}
          icon={FileText}
          colorClass="icon-blue"
          delay="delay-1"
          onClick={() => navigate('/graded-sheets')}
        />
        <StatCard
          title="Auto-Approved"
          value={stats.autoApproved.toLocaleString()}
          icon={CheckCircle2}
          colorClass="icon-green"
          delay="delay-2"
          onClick={() => navigate('/graded-sheets', { state: { status: 'AUTO_APPROVED' } })}
        />
        <StatCard
          title="Needs Review"
          value={stats.needsReview.toLocaleString()}
          icon={AlertCircle}
          colorClass="icon-orange"
          delay="delay-3"
          onClick={() => navigate('/graded-sheets', { state: { status: 'NEEDS_REVIEW' } })}
        />
        <PieChartCard
          title="Average Score"
          value={`${stats.averageScore}%`}
          percentage={stats.averageScore}
          delay="delay-3"
          onClick={() => navigate('/analytics')}
        />
      </section>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem', paddingRight: '1rem' }} className="animate-fade-in delay-3">
        <button 
          className="btn-secondary" 
          style={{ borderColor: 'var(--error-color)', color: 'var(--error-color)', backgroundColor: 'rgba(239, 68, 68, 0.1)' }}
          onClick={async () => {
            if (window.confirm("Are you sure you want to delete ALL data? This action cannot be undone.")) {
              try {
                await AppApi.clearAllData();
                loadData();
                alert("All evaluation data has been deleted successfully.");
              } catch (err) {
                alert("Failed to delete data: " + err.message);
              }
            }
          }}
        >
          <X size={18} /> Delete All Data
        </button>
      </div>

      {/* Recent Activity Section */}
      <section className="recent-activity glass-panel animate-fade-in delay-3" style={{ marginTop: '2rem' }}>
        <div className="section-header">
          <h2>Recent Evaluation Batches</h2>
          <button className="btn-secondary" onClick={() => navigate('/review')}>View All</button>
        </div>
        
        <div className="table-responsive">
          {batches.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              No evaluation batches recorded yet. Upload answer sheets to see real database records here!
            </div>
          ) : (
            <table className="activity-table">
              <thead>
                <tr>
                  <th>Batch ID</th>
                  <th>Subject</th>
                  <th>Date</th>
                  <th>Sheets</th>
                  <th>Status</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch, idx) => (
                  <tr key={batch.id} style={{ animationDelay: `${0.4 + idx * 0.1}s` }} className="animate-fade-in">
                    <td className="font-mono">{batch.id}</td>
                    <td className="font-semibold">{batch.subject}</td>
                    <td className="text-muted">{batch.date}</td>
                    <td>{batch.total}</td>
                    <td>
                      <span className={`badge badge-status-${batch.status.toLowerCase().replace(' ', '-')}`}>
                        {batch.status}
                      </span>
                    </td>
                    <td>
                      <div className="progress-bar-container">
                        <div 
                          className="progress-bar" 
                          style={{ 
                            width: `${batch.progress}%`
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem', marginTop: '2rem' }}>
        {/* Re-evaluation Requests Section */}
        <section className="glass-panel animate-fade-in delay-4">
          <div className="section-header">
            <h2>Re-evaluation Requests</h2>
            <span className="badge badge-status-processing">{reevalRequests.length} Pending</span>
          </div>
          
          <div className="table-responsive">
            <table className="activity-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Subject</th>
                  <th>Reason</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reevalRequests.map((req) => (
                  <tr key={req.id}>
                    <td className="font-semibold">{req.student}</td>
                    <td>{req.subject}</td>
                    <td className="text-muted" style={{ maxWidth: '150px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={req.reason}>
                      {req.reason}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button 
                          className="btn-secondary" 
                          style={{ padding: '4px 8px', borderColor: 'var(--success-color)', color: 'var(--success-color)' }} 
                          onClick={() => alert(`Reviewing ${req.id}`)}
                          title="Approve"
                        >
                          <CheckCircle2 size={14} />
                        </button>
                        <button 
                          className="btn-secondary" 
                          style={{ padding: '4px 8px', borderColor: 'var(--error-color)', color: 'var(--error-color)' }} 
                          onClick={() => alert(`Dismissing ${req.id}`)}
                          title="Dismiss"
                        >
                          <ThumbsDown size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Class Insights Section */}
        <section className="glass-panel animate-fade-in delay-5" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="section-header" style={{ marginBottom: 0 }}>
            <h2>Class Insights</h2>
          </div>
          
          <div className="stat-card" style={{ background: 'var(--bg-primary)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--success-color)' }}>
              <Users size={20} />
              <h3 style={{ fontSize: '1.2rem', margin: 0 }}>Top Performers</h3>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--text-primary)' }}>
              <li style={{ marginBottom: '5px' }}>Priya Sharma (95%)</li>
              <li style={{ marginBottom: '5px' }}>Ravi Kumar (90%)</li>
            </ul>
          </div>

          <div className="stat-card" style={{ background: 'var(--bg-primary)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--warning-color)' }}>
              <AlertCircle size={20} />
              <h3 style={{ fontSize: '1.2rem', margin: 0 }}>Topics Needing Attention</h3>
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--text-primary)' }}>
              <li style={{ marginBottom: '5px' }}>BST Search Operation & Recursion Analysis</li>
            </ul>
          </div>
        </section>
      </div>

      {chartModalOpen && (
        <div className="modal-overlay animate-fade-in" onClick={() => setChartModalOpen(false)} style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', 
          backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div className="glass-panel" style={{ width: '400px', padding: '2rem', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
            <h3>Average Class Score</h3>
            <p style={{ fontSize: '2.5rem', fontWeight: 700, margin: '1rem 0', color: 'var(--accent-primary)' }}>
              {stats.averageScore}%
            </p>
            <p className="text-muted">Calculated dynamically across all evaluated student answer sheets stored in SQLite database.</p>
            <button className="btn-primary" style={{ marginTop: '1.5rem' }} onClick={() => setChartModalOpen(false)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
