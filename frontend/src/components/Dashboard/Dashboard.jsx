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

  const handleNewCase = () => navigate('/new-case');
  const handleViewCase = (caseId) => navigate(`/case/${caseId}`);

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
                  <span className="arrow-icon">→</span>
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
