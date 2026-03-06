import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { caseAPI } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import './Dashboard.css';

function Dashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteModalConfig, setDeleteModalConfig] = useState({ isOpen: false, caseId: null });
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const response = await caseAPI.getMyCases();
      setCases(response.data);
    } catch (err) {
      setError('Failed to load cases');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewCase = () => navigate('/new-case');
  const handleViewCase = (caseId) => navigate(`/case/${caseId}`);

  const handleDeleteCase = async (e, caseId) => {
    e.stopPropagation();
    setDeleteModalConfig({ isOpen: true, caseId });
  };

  const confirmDelete = async () => {
    const { caseId } = deleteModalConfig;
    if (!caseId) return;
    try {
      await caseAPI.deleteCase(caseId);
      setCases(cases.filter(c => c.caseId !== caseId));
      setDeleteModalConfig({ isOpen: false, caseId: null });
    } catch (err) {
      alert(`Failed to delete case: ${err.response?.data?.message || JSON.stringify(err.response?.data) || err.message}`);
      console.error(err);
    }
  };

  const cancelDelete = () => {
    setDeleteModalConfig({ isOpen: false, caseId: null });
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed': return 'Completed';
      case 'ready': return 'Analysis Ready';
      case 'in_progress': return 'In Progress';
      default: return 'Draft';
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header glass-card">
        <div className="header-content">
          <div className="user-welcome">
            <h1>Hello, {user?.fullName || 'Counsel'}</h1>
            <p className="header-subtitle">Your Case Management Console</p>
          </div>
          <div className="header-actions">
            <ThemeToggle />
            <button onClick={handleNewCase} className="btn btn-primary">
              <span className="icon-plus">+</span> New Case
            </button>
            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="dashboard-content section-padding">
        {error && (
          <div className="alert-box">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p className="text-muted">Retrieving your legal brief...</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="empty-state glass-card">
            <div className="empty-icon">📂</div>
            <h2>No Cases Found</h2>
            <p>Start your first legal consultation by clicking 'New Case'.</p>
            <button onClick={handleNewCase} className="btn btn-primary">
              Create New Case
            </button>
          </div>
        ) : (
          <div className="cases-grid">
            {cases.map((caseItem) => (
              <div
                key={caseItem.caseId}
                className="case-card glass-card"
                onClick={() => handleViewCase(caseItem.caseId)}
              >
                <div className="case-header">
                  <span className={`status-badge status-${caseItem.status}`}>
                    {getStatusLabel(caseItem.status)}
                  </span>
                  <span className="case-ref">#{caseItem.referenceNumber.substring(0, 8)}...</span>
                </div>

                <div className="case-body">
                  <h3 className="case-title">{caseItem.subCategory?.replace('_', ' ')}</h3>
                  <p className="case-type">{caseItem.issueType?.replace('_', ' ')}</p>

                  <div className="meta-info">
                    {caseItem.suggestedAuthority && (
                      <div className="meta-item">
                        <span className="label">Authority</span>
                        <span className="value">{caseItem.suggestedAuthority}</span>
                      </div>
                    )}
                  </div>

                  <div className="case-progress">
                    <div className="progress-label">
                      <span>Analysis Completeness</span>
                      <span>{Math.round((caseItem.completeness || 0) * 100)}%</span>
                    </div>
                    <div className="progress-track">
                      <div
                        className="progress-fill"
                        style={{ width: `${(caseItem.completeness || 0) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="case-footer">
                  <span className="case-date">
                    Opened: {new Date(caseItem.createdAt).toLocaleDateString()}
                  </span>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {caseItem.status === 'draft' && (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '0.3rem 0.8rem', fontSize: '0.8rem', border: '1px solid #ef4444', color: '#ef4444', background: 'transparent' }}
                        onClick={(e) => handleDeleteCase(e, caseItem.caseId)}>
                        Delete
                      </button>
                    )}
                    <span className="arrow-icon">→</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {deleteModalConfig.isOpen && (
        <div className="modal-overlay" style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          backgroundColor: 'rgba(15, 23, 42, 0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000,
          backdropFilter: 'blur(4px)'
        }}>
          <div className="modal-content glass-card" style={{
            background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px', minWidth: '350px', maxWidth: '400px', width: '90%',
            border: '1px solid var(--glass-border)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🗑️</div>
            <h2 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Delete Draft?</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Are you sure you want to delete this case? This action cannot be undone.</p>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button
                className="btn btn-secondary"
                style={{ flex: 1, padding: '0.8rem' }}
                onClick={cancelDelete}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ flex: 1, padding: '0.8rem', background: '#ef4444', borderColor: '#ef4444' }}
                onClick={confirmDelete}>
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
