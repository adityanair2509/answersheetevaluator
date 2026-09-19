import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import './Login.css';

const Login = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState('teacher'); // 'teacher' or 'student'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    // If already logged in, go straight to dashboard
    const authData = localStorage.getItem('auth');
    if (authData) {
      try {
        const { expires } = JSON.parse(authData);
        if (Date.now() < expires) {
          navigate('/dashboard', { replace: true });
        }
      } catch (e) {}
    }
  }, [navigate]);

  const generateNameFromEmail = (emailStr) => {
    if (!emailStr) return role === 'teacher' ? 'Arnav Panwala' : 'Student User';
    const prefix = emailStr.split('@')[0];
    return prefix.split('.').map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
  };

  const setAuthData = (name, emailStr) => {
    const finalEmail = emailStr || email || (role === 'teacher' ? 'arnav.panwala@autoeval.edu' : 'student@autoeval.edu');
    const finalName = name || generateNameFromEmail(finalEmail);
    
    const expires = Date.now() + 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
    localStorage.setItem('auth', JSON.stringify({ 
      token: 'demo-token', 
      expires, 
      role,
      name: finalName,
      email: finalEmail
    }));
  };

  const handleLogin = (e) => {
    e.preventDefault();
    setError('');

    if (role === 'teacher') {
      if (email !== 'teacher@scribscore.com' || password !== 'teacher123') {
        setError('Invalid Teacher credentials.');
        return;
      }
    }

    setLoading(true);
    setTimeout(() => {
      setAuthData(null, email);
      navigate('/dashboard');
    }, 600);
  };

  const handleRegister = (e) => {
    e.preventDefault();
    setError('');
    
    const formEmail = e.target.querySelector('input[type="email"]')?.value;
    const formPassword = e.target.querySelector('input[type="password"]')?.value;
    const formName = e.target.querySelector('input[type="text"]')?.value;
    
    if (!formName || !formName.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!formEmail || !formEmail.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!formPassword || formPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    
    setLoading(true);
    setTimeout(() => {
      setAuthData(formName.trim(), formEmail.trim());
      navigate('/dashboard');
    }, 600);
  };

  return (
    <div className="login-page animate-fade-in" style={{ position: 'relative' }}>
      <div style={{ position: 'absolute', top: '2rem', left: '2rem', zIndex: 100 }}>
        <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: '#FAFAFA', textDecoration: 'none', fontSize: '0.95rem', fontWeight: 600, padding: '0.6rem 1.2rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid var(--border-glass)', borderRadius: '8px', backdropFilter: 'blur(10px)', transition: 'all 0.2s ease' }} onMouseOver={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.4)'} onMouseOut={(e) => e.currentTarget.style.borderColor = 'var(--border-glass)'}>
          <ArrowLeft size={18} /> Back to Home
        </Link>
      </div>
      <div className="flip-container">
        <input type="checkbox" id="signup_toggle" />
        <div className="form-wrapper">
          {/* Front: Login */}
          <form className="form_front" onSubmit={handleLogin}>
            <div className="login-header-inner">
              <h1>ScribScore</h1>
              <p>System Authentication</p>
            </div>
            
            <div className="role-selector" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', width: '100%' }}>
              <button 
                type="button" 
                onClick={() => setRole('teacher')} 
                className={role === 'teacher' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '0.5rem', fontSize: '0.9rem', margin: 0, justifyContent: 'center' }}
              >
                Teacher
              </button>
              <button 
                type="button" 
                onClick={() => setRole('student')} 
                className={role === 'student' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '0.5rem', fontSize: '0.9rem', margin: 0, justifyContent: 'center' }}
              >
                Student
              </button>
            </div>

            <input 
              placeholder="Email" 
              className="flip-input" 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input 
              placeholder="Password" 
              className="flip-input" 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            
            {error && <p style={{ color: '#ff3333', fontSize: '0.85rem', margin: '0 0 10px 0', textAlign: 'center' }}>{error}</p>}
            
            <button type="submit" className="flip-btn" disabled={loading}>
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
            <span className="switch">Don't have an account? 
                <label className="signup_tog" htmlFor="signup_toggle">
                    Sign Up
                </label>
            </span>
          </form>

          {/* Back: Sign Up */}
          <form className="form_back" onSubmit={handleRegister}>
            <div className="login-header-inner">
              <h1>ScribScore</h1>
              <p>System Registration</p>
            </div>

            <div className="role-selector" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', width: '100%' }}>
              <button 
                type="button" 
                onClick={() => setRole('teacher')} 
                className={role === 'teacher' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '0.5rem', fontSize: '0.9rem', margin: 0, justifyContent: 'center' }}
              >
                Teacher
              </button>
              <button 
                type="button" 
                onClick={() => setRole('student')} 
                className={role === 'student' ? 'btn-primary' : 'btn-secondary'}
                style={{ flex: 1, padding: '0.5rem', fontSize: '0.9rem', margin: 0, justifyContent: 'center' }}
              >
                Student
              </button>
            </div>

            <input placeholder="Firstname" className="flip-input" type="text" required />
            <input placeholder="Email" className="flip-input" type="email" required />
            <input placeholder="Password" className="flip-input" type="password" required />
            <button type="submit" className="flip-btn" disabled={loading}>
              {loading ? 'Registering...' : 'Register'}
            </button>
            <span className="switch">Already have an account? 
                <label className="signup_tog" htmlFor="signup_toggle">
                    Sign In
                </label>
            </span>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
