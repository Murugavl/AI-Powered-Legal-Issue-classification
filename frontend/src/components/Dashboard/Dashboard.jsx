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
  const [deleteModalConfig, setDeleteModalConfig] = useState({ isOpen: false, caseId: null, caseRef: '' });
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  useEffect(() => { fetchCases(); }, []);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const response = await caseAPI.getMyCases();
      // Sort newest first
      const sorted = (response.data || []).sort(
        (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
      );
      setCases(sorted);
    } catch (err) {
      setError('Failed to load cases. Please refresh.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewCase = () => navigate('/new-case');
  const handleViewCase = (caseId) => navigate(`/case/${caseId}`);

  /* ── Delete ─────────────────────────────────────────────── */
  const handleDeleteCase = (e, caseItem) => {
    e.stopPropagation();
    setDeleteModalConfig({ isOpen: true, caseId: caseItem.caseId, caseRef: caseItem.referenceNumber });
  };

  const confirmDelete = async () => {
    const { caseId } = deleteModalConfig;
    if (!caseId) return;
    try {
      await caseAPI.deleteCase(caseId);
      setCases(cases.filter(c => c.caseId !== caseId));
      setDeleteModalConfig({ isOpen: false, caseId: null, caseRef: '' });
    } catch (err) {
      alert(`Failed to delete case: ${err.response?.data?.message || err.message}`);
      console.error(err);
    }
  };

  const cancelDelete = () => setDeleteModalConfig({ isOpen: false, caseId: null, caseRef: '' });

  /* ── Status helpers ────────────────────────────────────── */
  const STATUS_META = {
    completed: { label: 'Completed', color: '#22c55e', icon: '✅' },
    ready: { label: 'Document Ready', color: '#6366f1', icon: '📄' },
    in_progress: { label: 'In Progress', color: '#eab308', icon: '⏳' },
    draft: { label: 'Draft', color: '#94a3b8', icon: '📝' },
  };
  const statusMeta = (status) => STATUS_META[status] || STATUS_META.draft;

  /* ── Stats bar ─────────────────────────────────────────── */
  const totalCases = cases.length;
  const completedCases = cases.filter(c => c.status === 'completed' || c.status === 'ready').length;
  const draftCases = cases.filter(c => c.status === 'draft' || c.status === 'in_progress').length;

  return (
    <div className="dashboard">
      {/* Header */}
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
            <button onClick={logout} className="btn btn-secondary">Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content section-padding">
        {error && <div className="alert-box">{error}</div>}

        {/* Stats row */}
        {!loading && cases.length > 0 && (
          <div style={{
            display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap',
          }}>
            {[
              { label: 'Total Cases', value: totalCases, color: '#6366f1' },
              { label: 'Completed', value: completedCases, color: '#22c55e' },
              { label: 'In Progress', value: draftCases, color: '#eab308' },
            ].map(stat => (
              <div key={stat.label} style={{
                background: 'var(--card-bg)', border: '1px solid var(--glass-border)',
                borderRadius: '10px', padding: '1rem 1.5rem', minWidth: '140px',
                borderLeft: `4px solid ${stat.color}`,
              }}>
                <div style={{ fontSize: '1.8rem', fontWeight: 700, color: stat.color }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <div className="loading-container">
            <div className="spinner"></div>
            <p className="text-muted">Retrieving your cases…</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="empty-state glass-card">
            <div className="empty-icon">📂</div>
            <h2>No Cases Yet</h2>
            <p>Start your first legal document preparation by clicking New Case.</p>
            <button onClick={handleNewCase} className="btn btn-primary">
              + Create New Case
            </button>
          </div>
        ) : (
          <div className="cases-grid">
            {cases.map((caseItem) => {
              const meta = statusMeta(caseItem.status);
              return (
                <div
                  key={caseItem.caseId}
                  className="case-card glass-card"
                  onClick={() => handleViewCase(caseItem.caseId)}
                  style={{ cursor: 'pointer', position: 'relative' }}
                >
                  {/* Status badge */}
                  <div className="case-header">
                    <span
                      className={`status-badge status-${caseItem.status}`}
                      style={{
                        background: `${meta.color}22`,
                        color: meta.color,
                        border: `1px solid ${meta.color}55`,
                        borderRadius: '6px', padding: '0.2rem 0.7rem',
                        fontSize: '0.75rem', fontWeight: 600,
                      }}>
                      {meta.icon} {meta.label}
                    </span>
                    <span className="case-ref" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      #{(caseItem.referenceNumber || '').substring(0, 12)}
                    </span>
                  </div>

                  {/* Body */}
                  <div className="case-body">
                    <h3 className="case-title" style={{ marginBottom: '0.3rem' }}>
                      {caseItem.subCategory?.replace(/_/g, ' ') || caseItem.issueType?.replace(/_/g, ' ') || 'Legal Complaint'}
                    </h3>
                    <p className="case-type" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '0.8rem' }}>
                      {caseItem.issueType?.replace(/_/g, ' ')}
                    </p>

                    {caseItem.suggestedAuthority && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                        🏛 {caseItem.suggestedAuthority}
                      </div>
                    )}

                    {/* Progress bar */}
                    <div className="case-progress" style={{ marginTop: '0.8rem' }}>
                      <div className="progress-label">
                        <span style={{ fontSize: '0.78rem' }}>Completeness</span>
                        <span style={{ fontSize: '0.78rem', fontWeight: 600 }}>
                          {Math.round((caseItem.completeness || 0) * 100)}%
                        </span>
                      </div>
                      <div className="progress-track">
                        <div
                          className="progress-fill"
                          style={{ width: `${(caseItem.completeness || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="case-footer">
                    <span className="case-date" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      📅 {new Date(caseItem.createdAt).toLocaleDateString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                    </span>
                    <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                      {/* Delete button — available for ALL cases */}
                      <button
                        style={{
                          padding: '0.25rem 0.7rem', fontSize: '0.75rem', borderRadius: '6px',
                          border: '1px solid rgba(239,68,68,0.5)', color: '#ef4444',
                          background: 'rgba(239,68,68,0.08)', cursor: 'pointer',
                        }}
                        onClick={(e) => handleDeleteCase(e, caseItem)}>
                        🗑 Delete
                      </button>
                      <span className="arrow-icon" style={{ color: 'var(--text-secondary)' }}>→</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {deleteModalConfig.isOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          backgroundColor: 'rgba(15, 23, 42, 0.82)', display: 'flex',
          justifyContent: 'center', alignItems: 'center', zIndex: 1000,
          backdropFilter: 'blur(4px)',
        }}>
          <div className="glass-card" style={{
            padding: '2rem', borderRadius: '14px', minWidth: '340px', maxWidth: '420px',
            width: '90%', textAlign: 'center',
            boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🗑️</div>
            <h2 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Delete Case?</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
              Ref: {deleteModalConfig.caseRef?.substring(0, 16)}
            </p>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
              This will permanently delete the case and its document. This cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button className="btn btn-secondary" style={{ flex: 1, padding: '0.8rem' }} onClick={cancelDelete}>
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
