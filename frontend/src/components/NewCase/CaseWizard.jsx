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
    user_full_name: 'Complainant Name',
    user_address: 'Address',
    user_city_state: 'City / State',
    user_phone: 'Phone Number',
    user_email: 'Email',
    incident_date: 'Date of Incident',
    incident_date_time: 'Date & Time of Incident',
    incident_location: 'Location',
    incident_description: 'Description',
    counterparty_name: 'Other Party Name',
    counterparty_upi_or_id: 'UPI ID / Account',
    counterparty_platform: 'Platform / Channel',
    counterparty_role: 'Other Party Role',
    counterparty_address: 'Other Party Address',
    financial_loss_value: 'Amount Involved',
    payment_method: 'Payment Method',
    payment_date: 'Payment Date',
    payment_reference: 'Payment Reference',
    evidence_available: 'Evidence Available',
    product_name: 'Product / Service',
    defect_description: 'Defect / Problem',
    stolen_items: 'Stolen / Missing Items',
    witness_details: 'Witnesses',
    harm_description: 'Impact / Harm',
    prior_complaints: 'Previous Actions Taken',
    rti_department: 'Government Department',
    information_sought: 'Information Requested',
    property_address: 'Property Address',
    rent_amount: 'Monthly Rent',
    deposit_amount: 'Security Deposit',
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
    // Split on newlines so they render as visual line breaks
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
   NextSteps — shown inline after document ready
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

    const messagesEndRef = useRef(null);
    useEffect(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

    useEffect(() => {
        if (!localStorage.getItem('token')) {
            alert('Please log in to continue.');
            navigate('/login');
        }
    }, [navigate]);

    /* ── apply an API response to state ────────────────────── */
    const applyResponse = (data) => {
        setLatestData(data);
        setEntities(data.extractedEntities || {});

        if (data.complete && data.documentPayload) {
            // Document ready
            try {
                const parsed = JSON.parse(data.documentPayload);
                setDocumentPayload(parsed);

                // Store next steps
                const steps = parsed.next_steps || data.nextSteps || [];
                setNextSteps(steps);
            } catch {
                setDocumentPayload({ raw: data.documentPayload });
            }
            setIsComplete(true);

            // Show document-ready message inline
            addSystemMessage(
                data.message ||
                'Your legal document has been prepared. You can preview and download it below.'
            );

            // Show next steps inline as a follow-up message (like GPT does)
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
            // Normal question, acknowledgment, or confirmation summary — all go inline in chat
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

    /* ── send text ──────────────────────────────────────────── */
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

    /* ── generate + download PDF ────────────────────────────── */
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
        } catch (err) {
            console.error(err);
            alert('Error generating PDF. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    /* ── file upload ────────────────────────────────────────── */
    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !sessionId) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            // Use central axios instance — picks up auth token + env base URL automatically
            const response = await sessionAPI.uploadEvidence(sessionId, formData);
            applyResponse(response.data);
        } catch (err) {
            console.error('Upload failed', err);
            addSystemMessage('File upload failed. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    /* ── voice input ────────────────────────────────────────── */
    const handleVoiceInput = async (audioFile) => {
        setLoading(true);
        addSystemMessage('🎤 Processing voice input...');

        try {
            const formData = new FormData();
            formData.append('audio', audioFile);
            formData.append('transcript', '');
            formData.append('language', 'en-IN');

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
            setLoading(false);
        }
    };

    /* ── delete session ─────────────────────────────────────── */
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

    const realEntities = Object.entries(entities).filter(([, v]) => isRealValue(v));

    /* ─────────────────────────────────────────────
       RENDER
    ───────────────────────────────────────────── */
    return (
        <div className="wizard-container">

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

                    {/* Typing indicator */}
                    {loading && (
                        <div className="typing-indicator">
                            <span className="dot" /><span className="dot" /><span className="dot" />
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input area / complete area */}
                {isComplete ? (
                    <div className="input-area complete-actions">
                        <button className="btn btn-primary" onClick={generateDocument} disabled={loading}>
                            📄 Download Bilingual PDF
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={() => navigate('/dashboard')}>
                            Go to Dashboard
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

                    {/* Evidence readiness */}
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
