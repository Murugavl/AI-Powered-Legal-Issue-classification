import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { caseAPI } from '../../utils/api';
import { useAuth } from '../../context/AuthContext';
import './Dashboard.css';

function Dashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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

  const handleNewCase = () => {
    navigate('/new-case');
  };

  const handleViewCase = (caseId) => {
    navigate(`/case/${caseId}`);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return '#4caf50';
      case 'ready':
        return '#2196f3';
      case 'in_progress':
        return '#ff9800';
      case 'draft':
        return '#9e9e9e';
      default:
        return '#757575';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'ready':
        return '📄';
      case 'in_progress':
        return '⏳';
      case 'draft':
        return '✏️';
      default:
        return '📋';
    }
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <div>
            <h1>Welcome, {user?.fullName || 'User'}!</h1>
            <p className="header-subtitle">Manage your legal document cases</p>
          </div>
          <div className="header-actions">
            <button onClick={handleNewCase} className="btn btn-primary">
              + New Case
            </button>
            <button onClick={logout} className="btn btn-secondary">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="dashboard-content">
        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading your cases...</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h2>No cases yet</h2>
            <p>Create your first legal document case to get started</p>
            <button onClick={handleNewCase} className="btn btn-primary">
              Create New Case
            </button>
          </div>
        ) : (
          <div className="cases-grid">
            {cases.map((caseItem) => (
              <div
                key={caseItem.caseId}
                className="case-card"
                onClick={() => handleViewCase(caseItem.caseId)}
              >
                <div className="case-header">
                  <div
                    className="case-status"
                    style={{ background: getStatusColor(caseItem.status) }}
                  >
                    <span className="status-icon">{getStatusIcon(caseItem.status)}</span>
                    <span className="status-text">{caseItem.status}</span>
                  </div>
                  <span className="case-ref">{caseItem.referenceNumber}</span>
                </div>

                <div className="case-body">
                  <h3>{caseItem.subCategory?.replace('_', ' ').toUpperCase()}</h3>
                  <p className="case-type">{caseItem.issueType?.replace('_', ' ')}</p>

                  {caseItem.suggestedAuthority && (
                    <p className="case-authority">
                      <strong>Authority:</strong> {caseItem.suggestedAuthority}
                    </p>
                  )}

                  <div className="case-progress">
                    <div className="progress-label">
                      <span>Completeness</span>
                      <span>{Math.round((caseItem.completeness || 0) * 100)}%</span>
                    </div>
                    <div className="progress-bar-small">
                      <div
                        className="progress-fill-small"
                        style={{ width: `${(caseItem.completeness || 0) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="case-footer">
                  <span className="case-date">
                    Created: {new Date(caseItem.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
