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
    user_full_name:        'Complainant Name',
    user_address:          'Address',
    user_city_state:       'City / State',
    user_phone:            'Phone Number',
    user_email:            'Email',
    incident_date:         'Date of Incident',
    incident_location:     'Location',
    incident_description:  'Description',
    counterparty_name:     'Other Party Name',
    counterparty_upi_or_id:'UPI ID / Account',
    counterparty_platform: 'Platform / Channel',
    counterparty_role:     'Other Party Role',
    counterparty_address:  'Other Party Address',
    financial_loss_value:  'Amount Involved',
    payment_method:        'Payment Method',
    payment_date:          'Payment Date',
    payment_reference:     'Payment Reference',
    evidence_available:    'Evidence Available',
    product_name:          'Product / Service',
    defect_description:    'Defect / Problem',
    stolen_items:          'Stolen / Missing Items',
    witness_details:       'Witnesses',
    harm_description:      'Impact / Harm',
    prior_complaints:      'Previous Actions Taken',
    rti_department:        'Government Department',
    information_sought:    'Information Requested',
    property_address:      'Property Address',
    rent_amount:           'Monthly Rent',
    deposit_amount:        'Security Deposit',
};

const labelFor = (key) =>
    KEY_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

/* Skip "Not available" values in the sidebar / summary */
const isRealValue = (v) =>
    v && !['not available', 'not applicable', 'null', 'unknown', ''].includes(String(v).toLowerCase().trim());

/* ─────────────────────────────────────────────
   Component
───────────────────────────────────────────── */

function CaseWizard() {
    const navigate = useNavigate();

    const [messages, setMessages] = useState([{
        id: 'greeting',
        sender: 'system',
        text: 'Vanakkam! I am Satta Vizhi, your legal document assistant. I am not a lawyer and I do not give legal advice — I only help you prepare documents. Please describe your legal issue in your own words.'
    }]);

    const [inputText,       setInputText]       = useState('');
    const [sessionId,       setSessionId]       = useState(null);
    const [loading,         setLoading]         = useState(false);
    const [entities,        setEntities]        = useState({});
    const [latestData,      setLatestData]      = useState(null);  // last API response
    const [isComplete,      setIsComplete]      = useState(false); // document is ready
    const [isConfirmation,  setIsConfirmation]  = useState(false); // show summary modal
    const [documentPayload, setDocumentPayload] = useState(null);  // parsed JSON from Python
    const [isUploading,     setIsUploading]     = useState(false);

    const messagesEndRef = useRef(null);
    useEffect(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages]);

    // Redirect if not logged in
    useEffect(() => {
        if (!localStorage.getItem('token')) {
            alert('Please log in to use Satta Vizhi.');
            navigate('/login');
        }
    }, [navigate]);

    /* ── apply an API response to state ── */
    const applyResponse = (data) => {
        setLatestData(data);
        setEntities(data.extractedEntities || {});

        if (data.complete && data.documentPayload) {
            // Document is ready — parse the JSON payload from Python
            try {
                const parsed = JSON.parse(data.documentPayload);
                setDocumentPayload(parsed);
            } catch {
                setDocumentPayload({ raw: data.documentPayload });
            }
            setIsComplete(true);
            setIsConfirmation(false);
            addSystemMessage(data.message || 'Your legal document is ready. You can preview and download it below.');

        } else if (data.confirmation || data.isConfirmation) {
            // Show summary modal for user to confirm
            setIsConfirmation(true);
            // Also show the confirmation message in chat so the user can read it
            addSystemMessage(data.message || 'Please review the information below and confirm.');

        } else if (data.message) {
            // Normal question / acknowledgment
            setIsConfirmation(false);
            addSystemMessage(data.message);
        }
    };

    const addSystemMessage = (text) => {
        setMessages(prev => [...prev, { id: Date.now() + Math.random(), sender: 'system', text }]);
    };

    /* ── send a text message ── */
    const handleSend = async () => {
        const text = inputText.trim();
        if (!text) return;

        setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text }]);
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

    /* ── user clicks "Yes, I Confirm" in the summary modal ── */
    const handleConfirmSummary = async () => {
        setIsConfirmation(false);
        setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: 'Yes, the above information is correct.' }]);
        setLoading(true);

        try {
            const response = await sessionAPI.answer(sessionId, 'Yes, the above information is correct.');
            applyResponse(response.data);
        } catch (err) {
            console.error(err);
            addSystemMessage("An error occurred during confirmation. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    /* ── user clicks "Cancel & Keep Editing" ── */
    const handleCancelConfirmation = async () => {
        setIsConfirmation(false);
        setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: 'No, I want to make changes.' }]);
        setLoading(true);

        try {
            const response = await sessionAPI.answer(sessionId, 'No, I want to make changes.');
            applyResponse(response.data);
        } catch (err) {
            console.error(err);
            addSystemMessage("Please tell me what you would like to change.");
        } finally {
            setLoading(false);
        }
    };

    /* ── generate + download the bilingual PDF ── */
    const generateDocument = async () => {
        if (!documentPayload) {
            alert('No document data available. Please complete the interview first.');
            return;
        }

        try {
            setLoading(true);
            const response = await documentAPI.generateBilingual(documentPayload);
            const blob = new Blob([response.data], { type: 'application/pdf' });
            const url  = window.URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href     = url;

            const docType = documentPayload.document_type || 'legal_document';
            a.download = `SattaVizhi_${docType}.pdf`;
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error(err);
            alert('Error generating PDF. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    /* ── evidence file upload ── */
    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !sessionId) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`http://localhost:8080/api/session/${sessionId}/evidence`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
                body: formData,
            });
            const data = await response.json();
            applyResponse(data);
        } catch (err) {
            console.error('Upload failed', err);
            addSystemMessage('File upload failed. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    /* ── voice input ── */
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
            // Remove the "processing" message
            setMessages(prev => prev.filter(m => m.text !== '🎤 Processing voice input...'));
            applyResponse(response.data);
        } catch (err) {
            console.error(err);
            addSystemMessage('Error processing voice input. Please try again or type your answer.');
        } finally {
            setLoading(false);
        }
    };

    /* ── delete session ── */
    const handleDeleteCase = async () => {
        if (!sessionId) return;
        if (!window.confirm('Are you sure you want to permanently delete this session? This cannot be undone.')) return;

        try {
            await sessionAPI.delete(sessionId);
            alert('Session deleted.');
            window.location.reload();
        } catch (err) {
            console.error(err);
            alert('Failed to delete session.');
        }
    };

    /* ── real entity entries for display ── */
    const realEntities = Object.entries(entities).filter(([, v]) => isRealValue(v));

    /* ─────────────────────────────────────────────
       RENDER
    ───────────────────────────────────────────── */
    return (
        <div className="wizard-container">

            {/* Header */}
            <div className="wizard-header">
                <h1>Satta Vizhi — Legal Assistant</h1>
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

                {/* ── Messages ── */}
                <div className="messages-area">
                    {messages.map(msg => (
                        <div key={msg.id} className={`message ${msg.sender}`}>
                            {msg.text}
                        </div>
                    ))}
                    {loading && (
                        <div className="typing-indicator">
                            <span>Satta Vizhi is typing…</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* ── Input / Complete area ── */}
                {isComplete ? (
                    <div className="input-area" style={{ justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                        <button className="btn btn-primary" onClick={generateDocument} disabled={loading}>
                            📄 Download Bilingual PDF
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={() => navigate('/dashboard')}
                            style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)', borderRadius: '8px', padding: '0.6rem 1.2rem', cursor: 'pointer' }}>
                            Go to Dashboard
                        </button>
                    </div>
                ) : (
                    <div className="input-area">
                        {/* Evidence upload */}
                        <label title="Upload evidence file" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'var(--text-muted)', fontSize: '1.2rem' }}>
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
                        <button className="btn-send" onClick={handleSend} disabled={loading || !inputText.trim()}>
                            ➜
                        </button>
                    </div>
                )}
            </div>

            {/* ── Sidebar: Discovered Facts ── */}
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

                    {/* Readiness score */}
                    {latestData?.readinessScore !== undefined && (
                        <div style={{ marginTop: '1.5rem' }}>
                            <div className="entities-title">Evidence Readiness</div>
                            <div style={{ background: '#334155', borderRadius: '10px', height: '20px', overflow: 'hidden' }}>
                                <div style={{
                                    width: `${latestData.readinessScore}%`,
                                    background: latestData.readinessScore >= 75 ? '#22c55e' : latestData.readinessScore >= 40 ? '#eab308' : '#ef4444',
                                    height: '100%',
                                    transition: 'width 0.5s ease-in-out'
                                }} />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem', fontSize: '0.85rem' }}>
                                <strong>{latestData.readinessScore}/100</strong>
                                <span style={{ color: 'var(--text-muted)' }}>
                                    {latestData.readinessScore >= 75 ? '✅ Strong evidence' :
                                     latestData.readinessScore >= 50 ? '🟡 Good — add more if possible' :
                                     latestData.readinessScore >= 25 ? '⚠️ Some evidence present' :
                                     '❌ Very limited evidence'}
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── Confirmation Modal ── */}
            {isConfirmation && (
                <div className="modal-overlay" style={{
                    position: 'fixed', inset: 0, backgroundColor: 'rgba(15,23,42,0.85)',
                    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px',
                        minWidth: '380px', maxWidth: '580px', width: '90%', maxHeight: '85vh', overflowY: 'auto',
                        border: '1px solid var(--glass-border)', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.6)'
                    }}>
                        <h2 style={{ marginBottom: '1.2rem', color: 'var(--text-primary)' }}>Information Summary</h2>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '1.2rem', fontSize: '0.9rem' }}>
                            Please review the information I have collected. If everything is correct, click "Yes, I Confirm" to generate your document.
                        </p>

                        <ul style={{ listStyle: 'none', padding: 0, marginBottom: '1.5rem' }}>
                            {realEntities.map(([key, value]) => (
                                <li key={key} style={{ padding: '0.7rem 0.8rem', background: 'var(--app-bg)', marginBottom: '0.4rem', borderRadius: '6px' }}>
                                    <strong style={{ color: 'var(--primary-color)' }}>{labelFor(key)}:</strong>{' '}
                                    <span style={{ color: 'var(--text-primary)' }}>{value}</span>
                                </li>
                            ))}
                        </ul>

                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" onClick={handleCancelConfirmation}
                                style={{ background: 'transparent', border: '1px solid var(--glass-border)', color: 'var(--text-primary)', borderRadius: '8px', padding: '0.6rem 1.2rem', cursor: 'pointer' }}>
                                Cancel &amp; Keep Editing
                            </button>
                            <button className="btn btn-primary" onClick={handleConfirmSummary}>
                                Yes, I Confirm
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default CaseWizard;
