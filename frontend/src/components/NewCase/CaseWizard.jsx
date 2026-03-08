import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI, documentAPI } from '../../utils/api';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import VoiceRecorder from './VoiceRecorder';
import './CaseWizard.css';

/* ─────────────────────────────────────────────
   Helpers
───────────────────────────────────────────── */

const KEY_LABELS = {
    complainant_name: 'Complainant Name',
    complainant_address: 'Address',
    complainant_city_state: 'City / State',
    complainant_phone: 'Phone Number',
    incident_date: 'Date of Incident',
    incident_time: 'Time of Incident',
    incident_location: 'Location',
    incident_description: 'Description',
    accused_description: 'Accused Description',
    property_details: 'Property / Loss Details',
    evidence_details: 'Evidence Available',
    police_status: 'Police Complaint Status',
    police_station_name: 'Police Station',
    // legacy keys (backward compat)
    user_full_name: 'Complainant Name',
    user_address: 'Address',
    user_city_state: 'City / State',
    user_phone: 'Phone Number',
    evidence_available: 'Evidence Available',
};

const labelFor = (key) =>
    KEY_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const isRealValue = (v) =>
    v && !['not available', 'not applicable', 'null', 'unknown', ''].includes(
        String(v).toLowerCase().trim()
    );

/* ─────────────────────────────────────────────
   MessageBubble — renders \n as proper line breaks
───────────────────────────────────────────── */
function MessageBubble({ msg }) {
    const lines = String(msg.text).split('\n');
    return (
        <div className={`message ${msg.sender}`}>
            {lines.map((line, i) => (
                <span key={i}>
                    {line}
                    {i < lines.length - 1 && <br />}
                </span>
            ))}
        </div>
    );
}

/* ─────────────────────────────────────────────
   NextSteps
───────────────────────────────────────────── */
function NextStepsMessage({ steps }) {
    if (!steps || steps.length === 0) return null;
    return (
        <div className="message system next-steps-message">
            <div className="next-steps-title">What to do next:</div>
            <ol className="next-steps-list">
                {steps.map((step, i) => (
                    <li key={i}>{step}</li>
                ))}
            </ol>
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
        <div style={{
            position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
            backgroundColor: 'rgba(10, 15, 30, 0.85)', display: 'flex',
            justifyContent: 'center', alignItems: 'center', zIndex: 2000,
            backdropFilter: 'blur(6px)', padding: '1rem',
        }}>
            <div style={{
                background: 'var(--card-bg, #1e293b)', borderRadius: '14px',
                border: '1px solid var(--glass-border, rgba(255,255,255,0.1))',
                boxShadow: '0 30px 60px rgba(0,0,0,0.6)',
                width: '100%', maxWidth: '820px', maxHeight: '90vh',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
            }}>
                {/* Header */}
                <div style={{
                    padding: '1.2rem 1.5rem', borderBottom: '1px solid var(--glass-border, rgba(255,255,255,0.1))',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    background: 'rgba(99,102,241,0.08)',
                }}>
                    <div>
                        <h2 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-primary, #e2e8f0)' }}>
                            📄 Document Preview
                        </h2>
                        <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary, #94a3b8)' }}>
                            Review your document before downloading
                        </p>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'transparent', border: 'none', color: 'var(--text-secondary, #94a3b8)',
                        fontSize: '1.4rem', cursor: 'pointer', lineHeight: 1,
                    }}>✕</button>
                </div>

                {/* Scrollable content */}
                <div style={{ overflowY: 'auto', padding: '1.5rem', flex: 1 }}>

                    {/* English Version */}
                    <div style={{ marginBottom: showBoth ? '2rem' : 0 }}>
                        {showBoth && (
                            <div style={{
                                fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.08em',
                                color: '#6366f1', marginBottom: '0.8rem', textTransform: 'uppercase',
                            }}>English Version</div>
                        )}
                        <pre style={{
                            background: 'rgba(255,255,255,0.04)', borderRadius: '8px',
                            padding: '1.2rem', fontFamily: "'Courier New', monospace",
                            fontSize: '0.82rem', lineHeight: 1.7,
                            color: 'var(--text-primary, #e2e8f0)',
                            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                            border: '1px solid rgba(255,255,255,0.06)',
                            margin: 0,
                        }}>
                            {english || '(No content)'}
                        </pre>
                    </div>

                    {/* Tamil / User-language Version */}
                    {showBoth && (
                        <div>
                            <div style={{
                                fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.08em',
                                color: '#22c55e', marginBottom: '0.8rem', textTransform: 'uppercase',
                            }}>Tamil / Regional Version</div>
                            <pre style={{
                                background: 'rgba(255,255,255,0.04)', borderRadius: '8px',
                                padding: '1.2rem', fontFamily: "'Noto Sans Tamil', 'Courier New', monospace",
                                fontSize: '0.88rem', lineHeight: 1.9,
                                color: 'var(--text-primary, #e2e8f0)',
                                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                                border: '1px solid rgba(255,255,255,0.06)',
                                margin: 0,
                            }}>
                                {userLang}
                            </pre>
                        </div>
                    )}

                    {/* Disclaimer box */}
                    {documentPayload.disclaimer_en && (
                        <div style={{
                            marginTop: '1.5rem', padding: '1rem',
                            background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
                            borderRadius: '8px', fontSize: '0.78rem', color: '#fca5a5', lineHeight: 1.6,
                        }}>
                            <strong>⚠ DISCLAIMER</strong><br />
                            {documentPayload.disclaimer_en}
                        </div>
                    )}
                </div>

                {/* Footer buttons */}
                <div style={{
                    padding: '1rem 1.5rem', borderTop: '1px solid var(--glass-border, rgba(255,255,255,0.1))',
                    display: 'flex', gap: '0.8rem', justifyContent: 'flex-end',
                    background: 'rgba(99,102,241,0.05)',
                }}>
                    <button
                        onClick={onClose}
                        style={{
                            padding: '0.6rem 1.4rem', borderRadius: '8px', cursor: 'pointer',
                            background: 'transparent', border: '1px solid rgba(255,255,255,0.2)',
                            color: 'var(--text-secondary, #94a3b8)', fontSize: '0.9rem',
                        }}>
                        ✕ Close
                    </button>
                    <button
                        onClick={onDownload}
                        disabled={loading}
                        style={{
                            padding: '0.6rem 1.6rem', borderRadius: '8px', cursor: 'pointer',
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            border: 'none', color: '#fff', fontWeight: 600, fontSize: '0.9rem',
                            opacity: loading ? 0.6 : 1,
                        }}>
                        {loading ? 'Generating PDF…' : '⬇ Download PDF'}
                    </button>
                </div>
            </div>
        </div>
    );
}

/* ─────────────────────────────────────────────
   Component
───────────────────────────────────────────── */

function CaseWizard() {
    const navigate = useNavigate();

    const [messages, setMessages] = useState([{
        id: 'greeting',
        sender: 'system',
        text: 'Vanakkam! I am your AI Legal Document Assistant. I am not a lawyer and I do not give legal advice — I only help you prepare documents.\n\nPlease describe your legal issue in your own words.',
    }]);

    const [inputText, setInputText] = useState('');
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [entities, setEntities] = useState({});
    const [latestData, setLatestData] = useState(null);
    const [isComplete, setIsComplete] = useState(false);
    const [documentPayload, setDocumentPayload] = useState(null);
    const [nextSteps, setNextSteps] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [showPreview, setShowPreview] = useState(false);

    const messagesEndRef = useRef(null);
    useEffect(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

    useEffect(() => {
        if (!localStorage.getItem('token')) {
            alert('Please log in to continue.');
            navigate('/login');
        }
    }, [navigate]);

    /* ── apply an API response to state ─────────── */
    const applyResponse = (data) => {
        setLatestData(data);
        setEntities(data.extractedEntities || {});

        if (data.complete && data.documentPayload) {
            try {
                const parsed = JSON.parse(data.documentPayload);
                setDocumentPayload(parsed);
                const steps = parsed.next_steps || data.nextSteps || [];
                setNextSteps(steps);
            } catch {
                setDocumentPayload({ raw: data.documentPayload });
            }
            setIsComplete(true);

            addSystemMessage(
                data.message ||
                'Your legal document has been prepared. You can preview and download it below.'
            );

            const steps = (() => {
                try {
                    const p = JSON.parse(data.documentPayload);
                    return p.next_steps || data.nextSteps || [];
                } catch { return data.nextSteps || []; }
            })();
            if (steps && steps.length > 0) {
                setNextSteps(steps);
                addNextStepsMessage(steps);
            }

        } else if (data.message) {
            addSystemMessage(data.message);
        }
    };

    const addSystemMessage = (text) => {
        setMessages(prev => [
            ...prev,
            { id: Date.now() + Math.random(), sender: 'system', text, type: 'normal' }
        ]);
    };

    const addNextStepsMessage = (steps) => {
        setMessages(prev => [
            ...prev,
            { id: Date.now() + Math.random(), sender: 'system', text: '', type: 'next_steps', steps }
        ]);
    };

    /* ── send text ─────────────────────────────── */
    const handleSend = async () => {
        const text = inputText.trim();
        if (!text || loading) return;

        setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text, type: 'normal' }]);
        setInputText('');
        setLoading(true);

        try {
            let response;
            if (!sessionId) {
                response = await sessionAPI.start(text);
                setSessionId(response.data.sessionId);
            } else {
                response = await sessionAPI.answer(sessionId, text);
            }
            applyResponse(response.data);
        } catch (err) {
            console.error(err);
            addSystemMessage("I'm sorry, I encountered an error. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    /* ── generate + download PDF ─────────────── */
    const generateDocument = async () => {
        if (!documentPayload) {
            alert('No document data available. Please complete the interview first.');
            return;
        }
        try {
            setLoading(true);
            const response = await documentAPI.generateBilingual(documentPayload);
            const blob = new Blob([response.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `LegalDocument_${documentPayload.document_type || 'document'}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
            setShowPreview(false);
        } catch (err) {
            console.error(err);
            alert('Error generating PDF. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    /* ── file upload ────────────────────────── */
    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !sessionId) return;
        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await sessionAPI.uploadEvidence(sessionId, formData);
            applyResponse(response.data);
        } catch (err) {
            console.error('Upload failed', err);
            addSystemMessage('File upload failed. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    /* ── voice input ─────────────────────────── */
    const handleVoiceInput = async (audioFile) => {
        setLoading(true);
        addSystemMessage('🎤 Processing voice input...');
        try {
            const transcript = window.prompt(
                'Please type the transcript of your voice input so it can be reviewed in text before submission:'
            );
            if (!transcript || !transcript.trim()) {
                addSystemMessage('Voice input was not submitted. Please provide transcript text and try again.');
                return;
            }

            const confirmText = window.prompt(
                `Transcript captured:\n\n${transcript}\n\nType YES to confirm this transcript exactly as shown.`
            );
            const transcriptConfirmed = (confirmText || '').trim().toUpperCase() === 'YES';
            if (!transcriptConfirmed) {
                addSystemMessage('Transcript not confirmed. Voice input was not submitted.');
                return;
            }

            const formData = new FormData();
            formData.append('audio', audioFile);
            formData.append('transcript', transcript.trim());
            formData.append('language', 'en-IN');
            formData.append('transcriptConfirmed', 'true');

            let sid = sessionId;
            if (!sid) {
                const startRes = await sessionAPI.start('Voice input');
                sid = startRes.data.sessionId;
                setSessionId(sid);
            }

            const response = await sessionAPI.answerVoice(sid, formData);
            setMessages(prev => prev.filter(m => m.text !== '🎤 Processing voice input...'));
            applyResponse(response.data);
        } catch (err) {
            console.error(err);
            addSystemMessage('Error processing voice input. Please try again or type your answer.');
        } finally {
            setMessages(prev => prev.filter(m => m.text !== '🎤 Processing voice input...'));
            setLoading(false);
        }
    };

    /* ── delete session ──────────────────────── */
    const handleDeleteCase = async () => {
        if (!sessionId) return;
        if (!window.confirm('Delete this session permanently? This cannot be undone.')) return;
        try {
            await sessionAPI.delete(sessionId);
            alert('Session deleted.');
            window.location.reload();
        } catch (err) {
            console.error(err);
            alert('Failed to delete session.');
        }
    };

    /* ── go to dashboard (preserves generated case) */
    const handleGoToDashboard = () => {
        // The case was already saved server-side during document generation.
        // Navigate directly — the dashboard will fetch and show it.
        navigate('/dashboard');
    };

    const realEntities = Object.entries(entities).filter(([, v]) => isRealValue(v));

    /* ─────────────────────────────────────────────
       RENDER
    ───────────────────────────────────────────── */
    return (
        <div className="wizard-container">

            {/* Preview Modal */}
            {showPreview && (
                <DocumentPreviewModal
                    documentPayload={documentPayload}
                    onDownload={generateDocument}
                    onClose={() => setShowPreview(false)}
                    loading={loading}
                />
            )}

            {/* Header */}
            <div className="wizard-header">
                <h1>AI Legal Document Assistant</h1>
                <p className="wizard-subhead">Not a lawyer · India only · Documents for informational purposes</p>
                <div style={{ position: 'absolute', right: '2rem', top: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {sessionId && (
                        <button
                            onClick={handleDeleteCase}
                            style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', color: '#ef4444', borderRadius: '6px', padding: '0.4rem 0.8rem', cursor: 'pointer', fontSize: '0.8rem' }}>
                            🗑 Delete Session
                        </button>
                    )}
                    <ThemeToggle />
                </div>
            </div>

            {/* Main layout */}
            <div className="chat-window">

                {/* Messages */}
                <div className="messages-area">
                    {messages.map(msg => (
                        msg.type === 'next_steps'
                            ? <NextStepsMessage key={msg.id} steps={msg.steps} />
                            : <MessageBubble key={msg.id} msg={msg} />
                    ))}

                    {loading && (
                        <div className="typing-indicator">
                            <span className="dot" /><span className="dot" /><span className="dot" />
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input / complete actions */}
                {isComplete ? (
                    <div className="input-area complete-actions">
                        {/* Preview button — prominent */}
                        <button
                            className="btn btn-primary"
                            onClick={() => setShowPreview(true)}
                            disabled={loading}
                            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            👁 Preview Document
                        </button>
                        {/* Download without preview */}
                        <button
                            className="btn btn-secondary"
                            onClick={generateDocument}
                            disabled={loading}
                            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            📄 Download PDF
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={handleGoToDashboard}>
                            📊 Go to Dashboard
                        </button>
                        <button
                            className="btn btn-ghost"
                            onClick={() => {
                                setMessages([{
                                    id: 'greeting',
                                    sender: 'system',
                                    text: 'Starting a new case. Please describe your legal issue in your own words.',
                                }]);
                                setSessionId(null);
                                setIsComplete(false);
                                setDocumentPayload(null);
                                setNextSteps([]);
                                setEntities({});
                                setLatestData(null);
                                setInputText('');
                            }}>
                            ➕ Start New Case
                        </button>
                    </div>
                ) : (
                    <div className="input-area">
                        <label title="Upload evidence file" className="attach-btn">
                            📎
                            <input type="file" hidden onChange={handleFileUpload} disabled={!sessionId || isUploading} />
                        </label>

                        <VoiceRecorder onRecordingComplete={handleVoiceInput} isProcessing={loading} />

                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Type your answer…"
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={loading}
                        />
                        <button
                            className="btn-send"
                            onClick={handleSend}
                            disabled={loading || !inputText.trim()}
                            aria-label="Send">
                            ➜
                        </button>
                    </div>
                )}
            </div>

            {/* Sidebar: Discovered Facts */}
            {realEntities.length > 0 && (
                <div className="entities-panel">
                    <div className="entities-title">Discovered Facts</div>
                    <div className="tag-cloud">
                        {realEntities.map(([key, value]) => (
                            <div key={key} className="data-tag">
                                <span>{labelFor(key)}:</span>
                                <strong>{value}</strong>
                            </div>
                        ))}
                    </div>

                    {latestData?.readinessScore !== undefined && (
                        <div style={{ marginTop: '1.5rem' }}>
                            <div className="entities-title">Evidence Readiness</div>
                            <div className="readiness-bar-bg">
                                <div className="readiness-bar-fill" style={{
                                    width: `${latestData.readinessScore}%`,
                                    background: latestData.readinessScore >= 75 ? '#22c55e'
                                        : latestData.readinessScore >= 40 ? '#eab308'
                                            : '#ef4444',
                                }} />
                            </div>
                            <div className="readiness-label-row">
                                <strong>{latestData.readinessScore}/100</strong>
                                <span>
                                    {latestData.readinessScore >= 75 ? '✅ Strong evidence'
                                        : latestData.readinessScore >= 50 ? '🟡 Good — add more if possible'
                                            : latestData.readinessScore >= 25 ? '⚠️ Some evidence present'
                                                : '❌ Very limited evidence'}
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default CaseWizard;
