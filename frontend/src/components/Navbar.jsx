import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Sparkles, LogOut } from 'lucide-react';

export const Navbar = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) return null;

  return (
    <header className="navbar">
      <div className="navbar-inner">
        
        {/* Brand Logo */}
        <Link to="/dashboard" className="brand-logo">
          <div className="brand-icon">
            <Sparkles size={16} />
          </div>
          <div>
            <div className="brand-title">InterviewQuest</div>
            <div className="brand-subtitle">Question Generator & Skill Matcher</div>
          </div>
        </Link>

        {/* Navigation Actions */}
        <div className="nav-actions">
          <Link
            to="/dashboard"
            className={`nav-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
          >
            Dashboard
          </Link>

          {/* User Profile & Sign Out */}
          <div className="user-profile">
            <div className="user-avatar">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <button
              onClick={handleLogout}
              className="btn-icon"
              title="Sign Out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>

      </div>
    </header>
  );
};
