import React, { useState, useRef } from 'react';
import { User, Mail, Briefcase, Activity, Settings, Bell, Lock, Save, Edit2, X } from 'lucide-react';
import './Account.css';

const Account = () => {
  const [isEditing, setIsEditing] = useState(false);
  const profileBackupRef = useRef(null);
  const [profile, setProfile] = useState({
    name: 'Professor Anderson',
    role: 'Administrator',
    department: 'Department of Computer Science',
    email: 'admin@autoeval.edu',
    id: 'EMP-88204'
  });

  const handleProfileChange = (e) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  return (
    <div className="account-container animate-fade-in">
      <header className="page-header">
        <div>
          <h1>User Profile</h1>
          <p className="subtitle">Manage your account settings and preferences.</p>
        </div>
      </header>

      <div className="account-grid">
        {/* Left Column: Profile & Stats */}
        <div className="account-column">
          <div className="glass-panel profile-card" style={{ position: 'relative' }}>
            {!isEditing ? (
              <button 
                className="icon-btn" 
                style={{ position: 'absolute', top: '1rem', right: '1rem' }}
                onClick={() => {
                  profileBackupRef.current = { ...profile };
                  setIsEditing(true);
                }}
                title="Edit Profile"
              >
                <Edit2 size={18} />
              </button>
            ) : null}
            <div className="profile-header-large">
              <div className="avatar-large">{profile.name.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase()}</div>
              <div className="profile-titles">
                {isEditing ? (
                  <input type="text" name="name" value={profile.name} onChange={handleProfileChange} className="brutalist-input" style={{ marginBottom: '0.5rem', padding: '0.5rem' }} />
                ) : (
                  <h2>{profile.name}</h2>
                )}
                <span className="badge badge-neutral">{profile.role}</span>
              </div>
            </div>
            
            <div className="profile-details">
              <div className="detail-row">
                <Briefcase size={16} className="text-muted" />
                {isEditing ? (
                  <input type="text" name="department" value={profile.department} onChange={handleProfileChange} className="brutalist-input" style={{ padding: '0.5rem' }} />
                ) : (
                  <span>{profile.department}</span>
                )}
              </div>
              <div className="detail-row">
                <Mail size={16} className="text-muted" />
                {isEditing ? (
                  <input type="email" name="email" value={profile.email} onChange={handleProfileChange} className="brutalist-input" style={{ padding: '0.5rem' }} />
                ) : (
                  <span>{profile.email}</span>
                )}
              </div>
              <div className="detail-row">
                <User size={16} className="text-muted" />
                {isEditing ? (
                  <input type="text" name="id" value={profile.id} onChange={handleProfileChange} className="brutalist-input" style={{ padding: '0.5rem' }} />
                ) : (
                  <span>ID: {profile.id}</span>
                )}
              </div>
              
              {isEditing && (
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                  <button className="btn-primary" onClick={() => setIsEditing(false)} style={{ flex: 1, padding: '0.5rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                    <Save size={16} /> Save
                  </button>
                  <button className="btn-secondary" onClick={() => { if (profileBackupRef.current) setProfile(profileBackupRef.current); setIsEditing(false); }} style={{ padding: '0.5rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem' }}>
                    <X size={16} /> Cancel
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="glass-panel stats-card">
            <h3><Activity size={18} className="text-accent" /> Evaluation Statistics</h3>
            <div className="stats-list">
              <div className="stat-item">
                <span className="stat-label">Total Sheets Graded</span>
                <span className="stat-value">12,450</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Avg. Time per Sheet</span>
                <span className="stat-value">4.2s</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">System Accuracy</span>
                <span className="stat-value text-success">98.4%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Preferences & Security */}
        <div className="account-column">
          <div className="glass-panel preferences-card">
            <h3><Settings size={18} className="text-blue" /> System Preferences</h3>
            
            <div className="preference-group">
              <label>Default Grading Strictness</label>
              <select className="brutalist-input" defaultValue="moderate">
                <option value="lenient">Lenient</option>
                <option value="moderate">Moderate</option>
                <option value="strict">Strict</option>
              </select>
              <p className="help-text">Adjusts the baseline threshold for AI confidence flags.</p>
            </div>

            <div className="preference-group toggle-group">
              <div className="toggle-info">
                <label>Email Notifications</label>
                <p className="help-text">Receive daily summaries of graded batches.</p>
              </div>
              <label className="account-toggle-switch">
                <input type="checkbox" defaultChecked />
                <span className="account-toggle-slider"></span>
              </label>
            </div>
            
            <button className="btn-primary" onClick={() => alert('Preferences saved!')}>
              <Save size={16} /> Save Preferences
            </button>
          </div>

          <div className="glass-panel security-card">
            <h3><Lock size={18} className="text-danger" /> Security</h3>
            
            <div className="preference-group">
              <label>Current Password</label>
              <input type="password" placeholder="••••••••" className="brutalist-input" />
            </div>
            <div className="preference-group">
              <label>New Password</label>
              <input type="password" placeholder="Enter new password" className="brutalist-input" />
            </div>
            
            <button className="btn-secondary text-danger" onClick={() => alert('Password update requested.')}>
              Update Password
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Account;
