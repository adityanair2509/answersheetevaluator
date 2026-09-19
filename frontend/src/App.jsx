import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import GradedSheets from './pages/GradedSheets';
import ScoreAnalytics from './pages/ScoreAnalytics';
import StudentDashboard from './pages/StudentDashboard';
import StudentUpload from './pages/StudentUpload';
import MyResults from './pages/MyResults';
import Upload from './pages/Upload';
import ExamSetup from './pages/ExamSetup';
import ReviewSession from './pages/ReviewSession';
import Export from './pages/Export';
import Account from './pages/Account';

import Login from './pages/Login';
import Landing from './pages/Landing';

// Info Pages
import Features from './pages/info/Features';
import Integrations from './pages/info/Integrations';
import Documentation from './pages/info/Documentation';
import Changelog from './pages/info/Changelog';
import About from './pages/info/About';
import Careers from './pages/info/Careers';
import Blog from './pages/info/Blog';
import Contact from './pages/info/Contact';
import Privacy from './pages/info/Privacy';
import Terms from './pages/info/Terms';
import Security from './pages/info/Security';
import CookieBanner from './components/CookieBanner';

// Check authentication status
const isAuthenticated = () => {
  const authData = localStorage.getItem('auth');
  if (!authData) return false;
  
  try {
    const { expires } = JSON.parse(authData);
    if (Date.now() > expires) {
      localStorage.removeItem('auth');
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
};

const RoleBasedDashboard = () => {
  const authData = localStorage.getItem('auth');
  let role = 'teacher';
  if (authData) {
    try {
      const parsed = JSON.parse(authData);
      role = parsed.role || 'teacher';
    } catch (e) {}
  }
  return role === 'student' ? <StudentDashboard /> : <Dashboard />;
};

const ProtectedRoute = ({ children }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const Layout = ({ children }) => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-color)' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '2rem', height: '100vh', overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <HashRouter>
      <CookieBanner />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        
        {/* Info Routes */}
        <Route path="/features" element={<Features />} />
        <Route path="/integrations" element={<Integrations />} />
        <Route path="/documentation" element={<Documentation />} />
        <Route path="/changelog" element={<Changelog />} />
        <Route path="/about" element={<About />} />
        <Route path="/careers" element={<Careers />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/security" element={<Security />} />
        
        {/* Authenticated Routes wrapped in Layout */}
        <Route path="/dashboard" element={<ProtectedRoute><Layout><RoleBasedDashboard /></Layout></ProtectedRoute>} />
        <Route path="/create-exam" element={<ProtectedRoute><Layout><ExamSetup /></Layout></ProtectedRoute>} />
        <Route path="/submit-sheet" element={<ProtectedRoute><Layout><StudentUpload /></Layout></ProtectedRoute>} />
        <Route path="/results" element={<ProtectedRoute><Layout><MyResults /></Layout></ProtectedRoute>} />
        <Route path="/upload" element={<ProtectedRoute><Layout><Upload /></Layout></ProtectedRoute>} />
        <Route path="/review" element={<ProtectedRoute><Layout><ReviewSession /></Layout></ProtectedRoute>} />
        <Route path="/graded-sheets" element={<ProtectedRoute><Layout><GradedSheets /></Layout></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><Layout><ScoreAnalytics /></Layout></ProtectedRoute>} />
        <Route path="/export" element={<ProtectedRoute><Layout><Export /></Layout></ProtectedRoute>} />
        <Route path="/account" element={<ProtectedRoute><Layout><Account /></Layout></ProtectedRoute>} />
      </Routes>
    </HashRouter>
  );
}

export default App;
