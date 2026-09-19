import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppApi } from '../api/client';
import { FileText, Award, Clock, ArrowRight, UploadCloud } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import ThemeToggle from '../components/ThemeToggle';
import './Dashboard.css';

const StatCard = ({ title, value, icon: Icon, trend, colorClass, delay, onClick }) => (
  <div 
    className={`stat-card glass-panel animate-fade-in ${delay} card-hover`}
    style={{ cursor: onClick ? 'pointer' : 'default' }}
    onClick={onClick}
  >
    <div className="stat-header">
      <div className={`stat-icon-wrapper ${colorClass}`}>
        <Icon size={24} />
      </div>
      <span className="stat-trend">{trend}</span>
    </div>
    <div className="stat-body">
      <h3>{value}</h3>
      <p>{title}</p>
    </div>
  </div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'var(--bg-primary)',
        border: '1px solid var(--border-glass)',
        padding: '10px',
        borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
      }}>
        <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{label}</p>
        <p style={{ margin: 0, color: 'var(--accent-primary)' }}>
          Score: {payload[0].value}%
        </p>
      </div>
    );
  }
  return null;
};

const StudentDashboard = () => {
  const navigate = useNavigate();

  const [recentTests, setRecentTests] = useState([]);
  const [stats, setStats] = useState({
    testsTaken: 0,
    averageScore: 0,
    pendingResults: 0,
    topSubject: 'N/A',
    topAverage: 0,
    topGrade: 'N/A'
  });
  const [progressData, setProgressData] = useState([]);

  useEffect(() => {
    AppApi.getMyResults().then(data => {
      setRecentTests(data.slice(0, 5)); // Keep latest 5 for recent activity
      
      const testsTaken = data.length;
      let totalScore = 0;
      let totalMax = 0;
      let pendingCount = 0;
      let subjectStats = {};
      let chartData = [];

      data.slice().reverse().forEach((sheet, idx) => { // Reverse to chronological for chart
        if (sheet.status !== 'Evaluated') {
           pendingCount++;
        }
        
        if (sheet.status === 'Evaluated') {
          const score = parseFloat(sheet.score) || 0;
          const max = parseFloat(sheet.total) || 10;
          totalScore += score;
          totalMax += max;
          
          if (!subjectStats[sheet.subject]) {
            subjectStats[sheet.subject] = { score: 0, max: 0 };
          }
          subjectStats[sheet.subject].score += score;
          subjectStats[sheet.subject].max += max;
          
          chartData.push({
            name: sheet.subject.split(' ')[0] + ' ' + (idx + 1), // shorthand name
            score: max > 0 ? Math.round((score / max) * 100) : 0
          });
        }
      });

      const averageScore = totalMax > 0 ? ((totalScore / totalMax) * 100).toFixed(1) : 0;
      
      let topSubject = 'N/A';
      let topAverage = 0;
      for (const subj in subjectStats) {
        const s = subjectStats[subj];
        const avg = (s.score / s.max) * 100;
        if (avg >= topAverage) {
          topAverage = avg;
          topSubject = subj;
        }
      }
      
      let topGrade = 'N/A';
      if (topAverage >= 90) topGrade = 'A+';
      else if (topAverage >= 80) topGrade = 'A';
      else if (topAverage >= 70) topGrade = 'B';
      else if (topAverage >= 60) topGrade = 'C';
      else if (topAverage > 0) topGrade = 'D';

      setStats({
        testsTaken,
        averageScore,
        pendingResults: pendingCount,
        topSubject,
        topAverage: topAverage.toFixed(1),
        topGrade
      });

      if (chartData.length === 0) {
        // Fallback mock if no evaluated tests
        chartData = [
          { name: 'Test 1', score: 0 }
        ];
      }
      setProgressData(chartData);
    });
  }, []);

  return (
    <div className="dashboard-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>Welcome back, Student</h1>
          <p className="subtitle">Here's your recent performance and pending evaluations.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <ThemeToggle />
          <button className="btn-secondary" onClick={() => navigate('/submit-sheet')}>
            <UploadCloud size={18} />
            Submit Answer Sheet
          </button>
          <button className="btn-primary" onClick={() => navigate('/results')}>
            <FileText size={18} />
            View All Results
          </button>
        </div>
      </header>

      <section className="stats-grid">
        <StatCard title="Tests Taken" value={stats.testsTaken} icon={FileText} trend="" colorClass="icon-blue" delay="delay-1" onClick={() => navigate('/results')} />
        <StatCard title="Average Score" value={`${stats.averageScore}%`} icon={Award} trend="" colorClass="icon-green" delay="delay-2" onClick={() => navigate('/results')} />
        <StatCard title="Pending Results" value={stats.pendingResults} icon={Clock} trend="" colorClass="icon-orange" delay="delay-3" onClick={() => navigate('/results')} />
        
        {/* Top Subject Highlight */}
        <div 
          className={`stat-card glass-panel animate-fade-in delay-3 card-hover`} 
          style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', cursor: 'pointer' }}
          onClick={() => navigate('/results')}
        >
          <div className="stat-body" style={{ flex: 1 }}>
            <div className="stat-header" style={{ marginBottom: '0.5rem' }}>
              <span className="stat-trend" style={{ color: 'var(--accent-primary)' }}>Top Subject</span>
            </div>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '4px' }}>{stats.topSubject}</h3>
            <p>{stats.topAverage}% Average</p>
          </div>
          <div style={{ width: '64px', height: '64px', borderRadius: '50%', border: '4px solid var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', fontWeight: 'bold' }}>
            {stats.topGrade}
          </div>
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '20px', marginTop: '20px' }}>
        
        {/* Progress Chart */}
        <section className="glass-panel animate-fade-in delay-2" style={{ padding: '20px' }}>
          <div className="section-header" style={{ marginBottom: '20px' }}>
            <h2>Performance Growth</h2>
          </div>
          <div style={{ width: '100%', height: '300px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={progressData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis 
                  dataKey="name" 
                  stroke="var(--text-secondary)" 
                  tick={{ fill: 'var(--text-secondary)' }} 
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  stroke="var(--text-secondary)" 
                  tick={{ fill: 'var(--text-secondary)' }} 
                  axisLine={false}
                  tickLine={false}
                  domain={[0, 100]}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line 
                  type="monotone" 
                  dataKey="score" 
                  stroke="var(--accent-primary)" 
                  strokeWidth={3}
                  dot={{ fill: 'var(--accent-primary)', strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: '#fff', stroke: 'var(--accent-primary)' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Recent Activity */}
        <section className="recent-activity glass-panel animate-fade-in delay-3" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div className="section-header" style={{ marginBottom: '15px' }}>
            <h2>Recent Tests</h2>
            <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '0.8rem' }} onClick={() => navigate('/results')}>
              See All <ArrowRight size={14} style={{ marginLeft: '4px' }} />
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', flex: 1 }}>
            {recentTests.length === 0 && (
              <p className="text-muted" style={{ textAlign: 'center', marginTop: '2rem' }}>No recent tests found.</p>
            )}
            {recentTests.map((test) => (
              <div key={test.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '15px', borderBottom: '1px solid var(--border-glass)' }}>
                <div>
                  <h4 style={{ margin: '0 0 5px 0', fontSize: '1rem' }}>{test.subject}</h4>
                  <span className="text-muted" style={{ fontSize: '0.85rem' }}>{test.date} • {test.id}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '5px' }}>
                  <span style={{ fontWeight: 'bold' }}>{test.status === 'Evaluated' ? `${test.score}/${test.total}` : 'Pending'}</span>
                  <span className={`badge badge-status-${test.status.toLowerCase().replace(' ', '-')}`} style={{ padding: '2px 6px', fontSize: '0.7rem' }}>
                    {test.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

      </div>
    </div>
  );
};

export default StudentDashboard;
