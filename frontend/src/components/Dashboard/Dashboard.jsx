import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI } from '../../utils/api';
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

  // Dashboard uses sessionAPI.getSessions() — sessions are what Satta Vizhi creates
  const fetchCases = async () => {
    try {
      setLoading(true);
      const response = await sessionAPI.getSessions();
      const sorted = (response.data || []).sort(
        (a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt)
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

  // Open a session — pass it via router state so CaseWizard can restore it
  const handleViewCase = (s) => navigate('/new-case', { state: { session: s } });

  /* ── Delete ─────────────────────────────────────────────── */
  const handleDeleteCase = (e, s) => {
    e.stopPropagation();
    setDeleteModalConfig({ isOpen: true, caseId: s.sessionId, caseRef: s.sessionId?.substring(0, 8) });
  };

  const confirmDelete = async () => {
    const { caseId } = deleteModalConfig;
    if (!caseId) return;
    try {
      await sessionAPI.delete(caseId);
      setCases(cases.filter(c => c.sessionId !== caseId));
      setDeleteModalConfig({ isOpen: false, caseId: null, caseRef: '' });
    } catch (err) {
      alert(`Failed to delete: ${err.response?.data?.message || err.message}`);
      console.error(err);
    }
  };

  const cancelDelete = () => setDeleteModalConfig({ isOpen: false, caseId: null, caseRef: '' });

  /* ── Helpers ────────────────────────────────────────────── */
  const STATUS_META = {
    COMPLETED: { label: 'Completed',   color: '#22c55e', icon: '✅' },
    ACTIVE:    { label: 'In Progress', color: '#eab308', icon: '⏳' },
    ABANDONED: { label: 'Abandoned',   color: '#94a3b8', icon: '📝' },
  };
  const statusMeta = (s) => STATUS_META[s] || STATUS_META.ACTIVE;

  const intentLabel = (intent) => {
    if (!intent) return 'Legal Case';
    const part = intent.split('—')[0].trim();
    return part.length > 45 ? part.substring(0, 45) + '…' : part;
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return ''; }
  };

  const totalCases     = cases.length;
  const completedCases = cases.filter(c => c.status === 'COMPLETED').length;
  const activeCases    = cases.filter(c => c.status === 'ACTIVE').length;

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header glass-card">
        <div className="header-content">
          <div className="user-welcome">
            <h1>Hello, {user?.fullName || 'Counsel'} 👋</h1>
            <p className="header-subtitle">Your Legal Case Dashboard</p>
          </div>
          <div className="header-actions">
            <ThemeToggle />
            <button onClick={handleNewCase} className="btn btn-primary">
              ✎ New Case
            </button>
            <button onClick={logout} className="btn btn-secondary">⏻ Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content section-padding">
        {error && <div className="alert-box">{error}</div>}

        {/* Stats */}
        {!loading && cases.length > 0 && (
          <div className="stats-row">
            {[
              { label: 'Total Cases',  value: totalCases,     color: '#6366f1' },
              { label: 'Completed',    value: completedCases, color: '#22c55e' },
              { label: 'In Progress',  value: activeCases,    color: '#eab308' },
            ].map(stat => (
              <div key={stat.label} className="stat-card" style={{ borderLeftColor: stat.color }}>
                <div className="stat-value" style={{ color: stat.color }}>{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <div className="loading-container">
            <div className="spinner" />
            <p className="text-muted">Retrieving your cases…</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="empty-state glass-card">
            <div className="empty-icon">📂</div>
            <h2>No Cases Yet</h2>
            <p>Start your first legal document preparation by clicking New Case.</p>
            <button onClick={handleNewCase} className="btn btn-primary">✎ Create New Case</button>
          </div>
        ) : (
          <div className="cases-grid">
            {cases.map((s) => {
              const meta = statusMeta(s.status);
              return (
                <div
                  key={s.sessionId}
                  className="case-card glass-card"
                  onClick={() => handleViewCase(s)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Status badge */}
                  <div className="case-header">
                    <span className="status-badge" style={{
                      background: `${meta.color}22`,
                      color: meta.color,
                      border: `1px solid ${meta.color}55`,
                      borderRadius: '6px', padding: '0.2rem 0.7rem',
                      fontSize: '0.75rem', fontWeight: 600,
                    }}>
                      {meta.icon} {meta.label}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      #{s.sessionId?.substring(0, 8)}
                    </span>
                  </div>

                  {/* Body */}
                  <div className="case-body">
                    <h3 className="case-title">{intentLabel(s.detectedIntent)}</h3>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
                      {formatDate(s.updatedAt || s.createdAt)}
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="case-footer">
                    <button
                      style={{
                        padding: '0.25rem 0.7rem', fontSize: '0.75rem', borderRadius: '6px',
                        border: '1px solid rgba(239,68,68,0.5)', color: '#ef4444',
                        background: 'rgba(239,68,68,0.08)', cursor: 'pointer',
                      }}
                      onClick={(e) => handleDeleteCase(e, s)}>
                      🗑 Delete
                    </button>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                      Open →
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete modal */}
      {deleteModalConfig.isOpen && (
        <div style={{
          position: 'fixed', inset: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.82)',
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          zIndex: 1000, backdropFilter: 'blur(4px)',
        }}>
          <div className="glass-card" style={{
            padding: '2rem', borderRadius: '14px',
            minWidth: '340px', maxWidth: '420px', width: '90%',
            textAlign: 'center', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🗑️</div>
            <h2 style={{ marginBottom: '0.5rem' }}>Delete Case?</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
              ID: {deleteModalConfig.caseRef}
            </p>
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
              This will permanently delete this case and cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button className="btn btn-secondary" style={{ flex: 1, padding: '0.8rem' }} onClick={cancelDelete}>
                Cancel
              </button>
              <button className="btn btn-primary"
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
