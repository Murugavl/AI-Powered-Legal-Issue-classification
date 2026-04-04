import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { sessionAPI, documentAPI } from '../../utils/api';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import VoiceRecorder from './VoiceRecorder';
import { useAuth } from '../../context/AuthContext';
// For Vite/React apps, files in the 'public' folder should be accessed via root paths
const logo = '/satta_vizhi_logo.png';
import './CaseWizard.css';

/* ─────────────────────────────────────────────
   Helpers
───────────────────────────────────────────── */
const KEY_LABELS = {
    complainant_name: 'Complainant Name',
    complainant_address: 'Address',
    incident_date: 'Date of Incident',
    incident_location: 'Location',
    evidence_details: 'Evidence',
    police_station_name: 'Police Station',
    user_full_name: 'Name',
    user_phone: 'Phone',
    evidence_available: 'Evidence',
};
const labelFor = (key) =>
    KEY_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const isRealValue = (v) =>
    v && !['not available', 'not applicable', 'null', 'unknown', ''].includes(
        String(v).toLowerCase().trim()
    );

const formatDate = (iso) => {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return ''; }
};

const intentLabel = (intent) => {
    if (!intent) return 'Legal Case';
    // intent format: "Category — description..."
    const part = intent.split('—')[0].trim();
    return part.length > 30 ? part.substring(0, 30) + '…' : part;
};

/* ─────────────────────────────────────────────
   MessageBubble
───────────────────────────────────────────── */
function MessageBubble({ msg }) {
    const lines = String(msg.text).split('\n');
    return (
        <div className={`cw-message cw-msg-${msg.sender}`}>
            {msg.sender === 'system' && (
                <div className="cw-avatar">
                    <img src={logo} alt="Satta Vizhi" className="cw-avatar-img" />
                </div>
            )}
            <div className="cw-bubble">
                {lines.map((line, i) => (
                    <span key={i}>{line}{i < lines.length - 1 && <br />}</span>
                ))}
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   DocumentPreviewModal
───────────────────────────────────────────── */
function DocumentPreviewModal({ documentPayload, onDownload, onClose, loading }) {
    if (!documentPayload) return null;
    const english = documentPayload.english_content || documentPayload.user_language_content || '';
    const userLang = documentPayload.user_language_content || '';
    const showBoth = userLang && userLang !== english;

    return (
        <div className="cw-modal-overlay">
            <div className="cw-modal">
                <div className="cw-modal-header">
                    <div>
                        <h2>📄 Document Preview</h2>
                        <p>Review your document before downloading</p>
                    </div>
                    <button className="cw-modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="cw-modal-body">
                    {showBoth && <div className="cw-lang-badge english">English Version</div>}
                    <pre className="cw-doc-pre">{english || '(No content)'}</pre>
                    {showBoth && (
                        <>
                            <div className="cw-lang-badge regional" style={{ marginTop: '1.5rem' }}>Regional Version</div>
                            <pre className="cw-doc-pre cw-doc-pre-regional">{userLang}</pre>
                        </>
                    )}
                    {documentPayload.disclaimer_en && (
                        <div className="cw-disclaimer-box">
                            <strong>⚠ DISCLAIMER</strong><br />
                            {documentPayload.disclaimer_en}
                        </div>
                    )}
                </div>
                <div className="cw-modal-footer">
                    <button className="cw-btn cw-btn-ghost" onClick={onClose}>✕ Close</button>
                    <button className="cw-btn cw-btn-primary" onClick={onDownload} disabled={loading}>
                        {loading ? 'Generating…' : '⬇ Download PDF'}
                    </button>
                </div>
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   Main CaseWizard
───────────────────────────────────────────── */
function CaseWizard() {
    const navigate = useNavigate();
    const location  = useLocation();
    const { user, logout } = useAuth();

    // ── Chat state ──────────────────────────────
    const [messages, setMessages] = useState([{
        id: 'greeting', sender: 'system', type: 'normal',
        text: 'Vanakkam! I am your AI Legal Document Assistant.\nI am not a lawyer and I do not give legal advice — I only help you prepare documents.\n\nPlease describe your legal issue in your own words.',
    }]);
    const [inputText, setInputText]   = useState('');
    const [sessionId, setSessionId]   = useState(null);
    const [loading, setLoading]       = useState(false);
    const [entities, setEntities]     = useState({});
    const [latestData, setLatestData] = useState(null);
    const [isComplete, setIsComplete] = useState(false);
    const [documentPayload, setDocumentPayload] = useState(null);
    const [isUploading, setIsUploading]         = useState(false);
    const [showPreview, setShowPreview]         = useState(false);
    const [currentIntent, setCurrentIntent]     = useState('');
    // Stores the full conversation per session: { [sessionId]: messages[] }
    const [sessionChats, setSessionChats] = useState({});

    // ── Sidebar state ───────────────────────────
    const [sessions, setSessions]               = useState([]);
    const [sidebarLoading, setSidebarLoading]   = useState(true);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    const messagesEndRef = useRef(null);
    useEffect(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

    useEffect(() => {
        if (!localStorage.getItem('token')) { navigate('/login'); return; }
        loadSessions();
    }, []);

    // ── Auto-open session passed from Dashboard (router state) ────────────
    useEffect(() => {
        if (location.state?.session) {
            openSession(location.state.session);
            // Clear the state so navigating back doesn’t re-open it
            navigate('/new-case', { replace: true, state: {} });
        }
    }, [location.state]);

    // ── Save current messages to sessionChats whenever they change ──
    useEffect(() => {
        if (sessionId) {
            setSessionChats(prev => ({ ...prev, [sessionId]: messages }));
        }
    }, [messages, sessionId]);

    // ── Cache documentPayload in sessionStorage whenever it changes ──
    useEffect(() => {
        if (sessionId && documentPayload && !documentPayload.raw) {
            try {
                sessionStorage.setItem(`doc_${sessionId}`, JSON.stringify(documentPayload));
            } catch {}
        }
    }, [documentPayload, sessionId]);

    const loadSessions = async () => {
        try {
            setSidebarLoading(true);
            const res = await sessionAPI.getSessions();
            const sorted = (res.data || []).sort(
                (a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt)
            );
            setSessions(sorted);
        } catch (e) {
            console.error('Failed to load sessions', e);
        } finally {
            setSidebarLoading(false);
        }
    };

    // ── Start a fresh chat ──────────────────────
    const startNewChat = () => {
        const greeting = {
            id: 'greeting', sender: 'system', type: 'normal',
            text: 'Starting a new case. Please describe your legal issue in your own words.',
        };
        setMessages([greeting]);
        setSessionId(null);
        setIsComplete(false);
        setDocumentPayload(null);
        setEntities({});
        setLatestData(null);
        setInputText('');
        setCurrentIntent('');
    };

    // ── Open an existing session from sidebar ───
    const openSession = async (s) => {
        setSessionId(s.sessionId);
        setLoading(true); // show loading during history fetch
        try {
            const res = await sessionAPI.getStatus(s.sessionId);
            const data = res.data;

            // Restore session state
            setCurrentIntent(data.detectedIntent || '');
            setEntities(data.extractedEntities || {});
            setLatestData({ readinessScore: data.readinessScore });
            setIsComplete(data.complete || (data.status === 'COMPLETED'));

            if (data.documentPayload) {
                try {
                    const parsed = typeof data.documentPayload === 'string' 
                        ? JSON.parse(data.documentPayload) 
                        : data.documentPayload;
                    setDocumentPayload(parsed);
                } catch (e) {
                    console.error("Payload parse error in openSession", e);
                    setDocumentPayload({ raw: data.documentPayload });
                }
            } else {
                setDocumentPayload(null);
            }

            if (data.history && data.history.length > 0) {
                setMessages(data.history);
                setSessionChats(prev => ({ ...prev, [s.sessionId]: data.history }));
            } else if (!data.complete) {
                // For active sessions with no history (new turn), show the greeting
                setMessages([{
                    id: 'greeting', sender: 'system', type: 'normal',
                    text: 'Vanakkam! I am your AI Legal Document Assistant.\nI am not a lawyer and I do not give legal advice — I only help you prepare documents.\n\nPlease describe your legal issue in your own words.',
                }]);
            } else {
                // Completed sessions with no history records yet: show nothing extra
                setMessages([]); 
            }
        } catch (err) {
            console.error('Failed to load session details', err);
            addMsg('system', 'Failed to load session history. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    // ── Apply API response ──────────────────────
    const applyResponse = (data) => {
        setLatestData(data);
        if (data.detectedIntent) setCurrentIntent(data.detectedIntent);
        if (data.extractedEntities) setEntities(data.extractedEntities || {});
        
        const isNowComplete = data.complete || (data.status === 'COMPLETED');
        setIsComplete(isNowComplete);

        if (data.documentPayload) {
            try {
                const parsed = typeof data.documentPayload === 'string' 
                    ? JSON.parse(data.documentPayload) 
                    : data.documentPayload;
                setDocumentPayload(parsed);
            } catch (e) {
                console.error("Payload parse error in applyResponse", e);
                setDocumentPayload({ raw: data.documentPayload });
            }
        }

        if (data.message) {
            addMsg('system', data.message);
        }

        if (isNowComplete) {
            loadSessions(); // Refresh sidebar
        }
    };

    const addMsg = (sender, text) => setMessages(prev => [
        ...prev,
        { id: Date.now() + Math.random(), sender, text, type: 'normal' }
    ]);

    // ── Send message ────────────────────────────
    const handleSend = async () => {
        const text = inputText.trim();
        if (!text || loading) return;
        addMsg('user', text);
        setInputText('');
        setLoading(true);
        try {
            let res;
            if (!sessionId) {
                res = await sessionAPI.start(text);
                setSessionId(res.data.sessionId);
                loadSessions();
            } else {
                res = await sessionAPI.answer(sessionId, text);
            }
            applyResponse(res.data);
        } catch (err) {
            console.error(err);
            addMsg('system', "I'm sorry, I encountered an error. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    // ── Download PDF ────────────────────────────
    const generateDocument = async () => {
        if (!documentPayload) return;
        try {
            setLoading(true);
            const res = await documentAPI.generateBilingual(documentPayload);
            const blob = new Blob([res.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `LegalDocument_${documentPayload.document_type || 'document'}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            setShowPreview(false);
        } catch { alert('Error generating PDF. Please try again.'); }
        finally { setLoading(false); }
    };

    // ── File upload ─────────────────────────────
    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !sessionId) return;
        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await sessionAPI.uploadEvidence(sessionId, formData);
            applyResponse(res.data);
        } catch { addMsg('system', 'File upload failed. Please try again.'); }
        finally { setIsUploading(false); }
    };

    // ── Voice ───────────────────────────────────────────────────────────────
    // Receives a plain-text string directly from SpeechRecognition (via VoiceRecorder).
    // Processes it exactly like a typed message — no prompt, no blob upload needed.
    const handleVoiceInput = async (recognizedText) => {
        const text = (recognizedText || '').trim();
        if (!text || loading) return;

        // Show the transcribed text in the chat as a user message
        addMsg('user', `🎤 ${text}`);
        setLoading(true);
        try {
            let res;
            if (!sessionId) {
                res = await sessionAPI.start(text);
                setSessionId(res.data.sessionId);
                loadSessions();
            } else {
                res = await sessionAPI.answer(sessionId, text);
            }
            applyResponse(res.data);
        } catch (err) {
            console.error(err);
            addMsg('system', "I'm sorry, I encountered an error processing your voice input. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    // ── Delete current session ──────────────────
    const handleDeleteSession = async () => {
        if (!sessionId) return;
        if (!window.confirm('Delete this session? This cannot be undone.')) return;
        try {
            await sessionAPI.delete(sessionId);
            startNewChat();
            loadSessions();
        } catch { alert('Failed to delete session.'); }
    };

    // ── Delete sidebar session ──────────────────
    const handleDeleteSidebarSession = async (e, sid) => {
        e.stopPropagation();
        if (!window.confirm('Delete this case?')) return;
        try {
            await sessionAPI.delete(sid);
            setSessions(prev => prev.filter(s => s.sessionId !== sid));
            setSessionChats(prev => { const c = { ...prev }; delete c[sid]; return c; });
            if (sid === sessionId) startNewChat();
        } catch { alert('Failed to delete.'); }
    };

    const realEntities = Object.entries(entities).filter(([k, v]) => isRealValue(v) && k !== '_language_');

    return (
        <div className="cw-root">

            {showPreview && (
                <DocumentPreviewModal
                    documentPayload={documentPayload}
                    onDownload={generateDocument}
                    onClose={() => setShowPreview(false)}
                    loading={loading}
                />
            )}

            {/* ═══ LEFT SIDEBAR ═══ */}
            <aside className={`cw-sidebar ${sidebarCollapsed ? 'cw-sidebar-collapsed' : ''}`}>

                {/* Brand + collapse */}
                <div className="cw-sidebar-top">
                    <div className="cw-sidebar-brand">
                        <img src={logo} alt="logo" className="cw-brand-logo" />
                        {!sidebarCollapsed && <span className="cw-brand-name">Satta Vizhi</span>}
                        <button className="cw-collapse-btn"
                            onClick={() => setSidebarCollapsed(p => !p)}
                            title={sidebarCollapsed ? 'Expand' : 'Collapse'}>
                            {sidebarCollapsed ? '›' : '‹'}
                        </button>
                    </div>

                    <button className="cw-new-chat-btn" onClick={startNewChat} title="New Case">
                        <span>✎</span>
                        {!sidebarCollapsed && <span>New Case</span>}
                    </button>
                </div>

                {/* Session list */}
                {!sidebarCollapsed && (
                    <div className="cw-session-list">
                        {sidebarLoading ? (
                            <div className="cw-sidebar-empty">Loading…</div>
                        ) : sessions.length === 0 ? (
                            <div className="cw-sidebar-empty">No previous cases</div>
                        ) : (
                            <>
                                <div className="cw-session-group-label">Recent Cases</div>
                                {sessions.map(s => (
                                    <div
                                        key={s.sessionId}
                                        className={`cw-session-item ${s.sessionId === sessionId ? 'cw-session-active' : ''}`}
                                        onClick={() => openSession(s)}
                                        title={s.detectedIntent || 'Legal Case'}
                                    >
                                        <span className="cw-session-icon">
                                            {s.status === 'COMPLETED' ? '✅' : '⏳'}
                                        </span>
                                        <div className="cw-session-info">
                                            <div className="cw-session-title">{intentLabel(s.detectedIntent)}</div>
                                            <div className="cw-session-date">{formatDate(s.updatedAt || s.createdAt)}</div>
                                        </div>
                                        <button
                                            className="cw-session-del"
                                            onClick={(e) => handleDeleteSidebarSession(e, s.sessionId)}
                                            title="Delete">✕</button>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                )}

                {/* User info at bottom */}
                {!sidebarCollapsed && (
                    <div className="cw-sidebar-footer">
                        <div className="cw-sidebar-user">
                            <div className="cw-user-avatar">
                                {(user?.fullName || 'U')[0].toUpperCase()}
                            </div>
                            <div className="cw-user-name">{user?.fullName || 'User'}</div>
                        </div>
                        <ThemeToggle />
                    </div>
                )}
            </aside>

            {/* ═══ MAIN AREA ═══ */}
            <main className="cw-main">

                {/* Top bar */}
                <div className="cw-topbar">
                    <div className="cw-topbar-title">
                        {currentIntent ? intentLabel(currentIntent) : 'AI Legal Document Assistant'}
                    </div>
                    <div className="cw-topbar-actions">
                        {sessionId && !isComplete && (
                            <button className="cw-btn cw-btn-ghost cw-btn-sm"
                                onClick={() => { if (window.confirm('Save and exit?')) navigate('/dashboard'); }}>
                                💾 Save & Exit
                            </button>
                        )}
                        {sessionId && (
                            <button className="cw-btn cw-btn-danger cw-btn-sm" onClick={handleDeleteSession}>
                                🗑
                            </button>
                        )}
                        {/* Logout — prominent red button in top-right */}
                        <button className="cw-logout-topbar" onClick={logout} title="Logout">
                            ⏻ Logout
                        </button>
                    </div>
                </div>

                {/* Messages */}
                <div className="cw-messages">
                    {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}

                    {loading && (
                        <div className="cw-message cw-msg-system">
                            <div className="cw-avatar">
                                <img src={logo} alt="thinking" className="cw-avatar-img" />
                            </div>
                            <div className="cw-bubble cw-typing">
                                <span className="cw-dot" /><span className="cw-dot" /><span className="cw-dot" />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Facts strip */}
                {realEntities.length > 0 && (
                    <div className="cw-facts-strip">
                        {realEntities.slice(0, 5).map(([key, value]) => (
                            <span key={key} className="cw-fact-chip">
                                <span className="cw-fact-key">{labelFor(key)}</span>
                                <span className="cw-fact-val">
                                    {String(value).length > 22 ? String(value).substring(0, 22) + '…' : value}
                                </span>
                            </span>
                        ))}
                        {realEntities.length > 5 && (
                            <span className="cw-fact-more">+{realEntities.length - 5} more</span>
                        )}
                        {latestData?.readinessScore !== undefined && (
                            <span className="cw-readiness-chip" style={{
                                background: latestData.readinessScore >= 75 ? 'rgba(34,197,94,0.15)'
                                    : latestData.readinessScore >= 40 ? 'rgba(234,179,8,0.15)' : 'rgba(239,68,68,0.15)',
                                color: latestData.readinessScore >= 75 ? '#16a34a'
                                    : latestData.readinessScore >= 40 ? '#b45309' : '#dc2626',
                                border: '1px solid currentColor',
                            }}>
                                Evidence {latestData.readinessScore}/100
                            </span>
                        )}
                    </div>
                )}

                {/* Input / complete */}
                {isComplete ? (
                    <div className="cw-complete-bar">
                        <button className="cw-btn cw-btn-primary" onClick={() => setShowPreview(true)} disabled={loading}>
                            👁 Preview
                        </button>
                        <button className="cw-btn cw-btn-secondary" onClick={generateDocument} disabled={loading}>
                            📄 Download PDF
                        </button>
                        <button className="cw-btn cw-btn-secondary" onClick={() => navigate('/dashboard')}>
                            📊 Dashboard
                        </button>
                        <button className="cw-btn cw-btn-ghost" onClick={startNewChat}>
                            ✎ New Case
                        </button>
                    </div>
                ) : (
                    <div className="cw-input-bar">
                        <label className="cw-attach" title="Upload evidence">
                            📎
                            <input type="file" hidden onChange={handleFileUpload}
                                disabled={!sessionId || isUploading} />
                        </label>
                        <VoiceRecorder 
                            onRecordingComplete={handleVoiceInput} 
                            isProcessing={loading} 
                            language={entities._language_} 
                        />
                        <input
                            className="cw-input"
                            type="text"
                            placeholder="Describe your issue or type your answer…"
                            value={inputText}
                            onChange={e => setInputText(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={loading}
                        />
                        <button
                            className="cw-send-btn"
                            onClick={handleSend}
                            disabled={loading || !inputText.trim()}
                            aria-label="Send">↑</button>
                    </div>
                )}
            </main>
        </div>
    );
}

export default CaseWizard;
