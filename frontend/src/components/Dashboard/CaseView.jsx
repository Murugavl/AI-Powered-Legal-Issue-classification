import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { caseAPI } from '../../utils/api';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import './Dashboard.css';

function CaseView() {
    const { caseId } = useParams();
    const navigate = useNavigate();
    const [caseData, setCaseData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showDeleteModal, setShowDeleteModal] = useState(false);

    useEffect(() => {
        fetchCaseDetails();
    }, [caseId]);

    const fetchCaseDetails = async () => {
        try {
            setLoading(true);
            const response = await caseAPI.getById(caseId);
            setCaseData(response.data);
        } catch (err) {
            setError('Failed to load case details.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteDraft = () => {
        setShowDeleteModal(true);
    };

    const confirmDeleteDraft = async () => {
        try {
            await caseAPI.deleteCase(caseId);
            navigate('/dashboard');
        } catch (err) {
            alert(`Failed to delete case: ${err.response?.data || err.message}`);
            console.error(err);
        }
    };

    const cancelDeleteDraft = () => {
        setShowDeleteModal(false);
    };

    if (loading) {
        return (
            <div className="dashboard">
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p className="text-muted">Loading case details...</p>
                </div>
            </div>
        );
    }

    if (error || !caseData) {
        return (
            <div className="dashboard">
                <div className="alert-box">{error || 'Case not found'}</div>
                <button onClick={() => navigate('/dashboard')} className="btn btn-secondary" style={{ margin: '2rem' }}>Back to Dashboard</button>
            </div>
        );
    }

    return (
        <div className="dashboard">
            <header className="dashboard-header glass-card">
                <div className="header-content">
                    <div className="user-welcome">
                        <h1>Case Reference #{caseData.referenceNumber?.substring(0, 8)}</h1>
                        <p className="header-subtitle">Status: {caseData.status?.toUpperCase()}</p>
                    </div>
                    <div className="header-actions">
                        <ThemeToggle />
                        {caseData.status === 'draft' && (
                            <button onClick={handleDeleteDraft} className="btn btn-secondary" style={{ border: '1px solid #ef4444', color: '#ef4444' }}>
                                Delete Draft
                            </button>
                        )}
                        <button onClick={() => navigate('/dashboard')} className="btn btn-secondary">
                            Back to Dashboard
                        </button>
                    </div>
                </div>
            </header>

            <div className="dashboard-content section-padding">
                <div className="glass-card" style={{ padding: '2rem' }}>
                    <h2 style={{ color: 'var(--primary-color)', marginBottom: '1rem' }}>
                        {caseData.issueType?.replace(/_/g, ' ')}
                    </h2>
                    {caseData.subCategory && (
                        <h3 style={{ marginBottom: '2rem', color: 'var(--text-secondary)' }}>
                            Action: {caseData.subCategory}
                        </h3>
                    )}

                    <h3 style={{ borderBottom: '1px solid var(--glass-border)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
                        Collected Facts
                    </h3>

                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {caseData.entities && Object.entries(caseData.entities).map(([key, info]) => {
                            if (info.value === 'EXPLICITLY_DENIED') return null;
                            return (
                                <li key={key} style={{ padding: '0.8rem', background: 'var(--app-bg)', marginBottom: '0.5rem', borderRadius: '6px' }}>
                                    <strong style={{ textTransform: 'capitalize', color: 'var(--primary-color)' }}>
                                        {key.replace(/_/g, ' ')}:
                                    </strong> {info.value || 'Not provided'}
                                </li>
                            );
                        })}
                    </ul>
                </div>
            </div>

            {showDeleteModal && (
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
                                onClick={cancelDeleteDraft}>
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                style={{ flex: 1, padding: '0.8rem', background: '#ef4444', borderColor: '#ef4444' }}
                                onClick={confirmDeleteDraft}>
                                Yes, Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default CaseView;
