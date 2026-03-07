import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import './Auth.css';

function Login() {
  const [formData, setFormData] = useState({
    phoneNumber: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // view: 'login' | 'forgot' | 'otp' | 'reset'
  const [view, setView] = useState('login');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const navigate = useNavigate();
  const { login } = useAuth();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
    setSuccess('');
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    if (!formData.phoneNumber) {
      setError('Please enter your phone number first');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await authAPI.forgotPassword({ phoneNumber: formData.phoneNumber });
      setSuccess(`OTP sent to ${formData.phoneNumber} ${res.data.otp ? '(Auto-filled for testing: ' + res.data.otp + ')' : ''}`);
      if (res.data.otp) {
        setOtp(res.data.otp);
      }
      setView('otp');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await authAPI.verifyOtp({ phoneNumber: formData.phoneNumber, otp });
      setSuccess('OTP verified. Please enter a new password.');
      setView('reset');
    } catch (err) {
      setError(err.response?.data?.message || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await authAPI.resetPassword({ phoneNumber: formData.phoneNumber, otp, newPassword });
      setSuccess('Password reset successfully. Please log in.');
      setView('login');
      setOtp('');
      setNewPassword('');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await authAPI.login(formData);
      const { token, phoneNumber, fullName, preferredLanguage } = response.data;

      login(token, { phoneNumber, fullName, preferredLanguage });
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="theme-toggle-absolute">
        <ThemeToggle />
      </div>
      <div className="auth-card glass-card">
        <div className="auth-header-logo">
          <img src="/satta_vizhi_logo.png" alt="Logo" className="auth-logo-img" />
        </div>
        <h1>
          {view === 'login' && 'Login'}
          {view === 'forgot' && 'Forgot Password'}
          {view === 'otp' && 'Verify OTP'}
          {view === 'reset' && 'Reset Password'}
        </h1>
        <p className="auth-subtitle">
          {view === 'login' && 'Welcome back to Satta Vizhi'}
          {view === 'forgot' && 'Enter your phone number to receive an OTP'}
          {view === 'otp' && 'Enter the OTP sent to your phone'}
          {view === 'reset' && 'Enter your new password'}
        </p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message" style={{ color: 'var(--success-color)', marginBottom: '1rem', padding: '10px', backgroundColor: 'rgba(46, 204, 113, 0.1)', borderRadius: '4px' }}>{success}</div>}

        {view === 'login' && (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="phoneNumber">Phone Number</label>
              <input
                type="tel"
                id="phoneNumber"
                name="phoneNumber"
                value={formData.phoneNumber}
                onChange={handleChange}
                placeholder="9876543210"
                required
                pattern="[0-9]{10}"
                title="Please enter a valid 10-digit phone number"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                required
                minLength="6"
              />
            </div>

            <div style={{ textAlign: 'right', marginBottom: '1rem' }}>
              <button
                type="button"
                onClick={() => setView('forgot')}
                style={{ background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', fontSize: '0.9rem' }}
              >
                Forgot Password?
              </button>
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        )}

        {view === 'forgot' && (
          <form onSubmit={handleForgotSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="phoneNumberForgot">Phone Number</label>
              <input
                type="tel"
                id="phoneNumberForgot"
                name="phoneNumber"
                value={formData.phoneNumber}
                onChange={handleChange}
                placeholder="9876543210"
                required
                pattern="[0-9]{10}"
                title="Please enter a valid 10-digit phone number"
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Sending OTP...' : 'Send OTP'}
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { setView('login'); setError(''); setSuccess(''); }}
              style={{ marginTop: '10px', width: '100%', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-color)' }}
            >
              Back to Login
            </button>
          </form>
        )}

        {view === 'otp' && (
          <form onSubmit={handleOtpSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="otp">Enter OTP</label>
              <input
                type="text"
                id="otp"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                placeholder="123456"
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify OTP'}
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => { setView('forgot'); setError(''); setSuccess(''); }}
              style={{ marginTop: '10px', width: '100%', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-color)' }}
            >
              Back
            </button>
          </form>
        )}

        {view === 'reset' && (
          <form onSubmit={handleResetSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="newPassword">New Password</label>
              <input
                type="password"
                id="newPassword"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                required
                minLength="6"
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>
        )}

        {view === 'login' && (
          <p className="auth-footer">
            Don't have an account? <a href="/register">Register here</a>
          </p>
        )}
      </div>
    </div>
  );
}

export default Login;
