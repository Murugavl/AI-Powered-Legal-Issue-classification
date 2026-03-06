import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI, documentAPI, caseAPI } from '../../utils/api';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import VoiceRecorder from './VoiceRecorder';
import './CaseWizard.css';

function CaseWizard() {
    const navigate = useNavigate();
    const [messages, setMessages] = useState([
        {
            id: 'greeting',
            sender: 'system',
            text: 'Hello. I am your AI Legal Assistant. Please describe your legal issue in your own words, and I will help you draft the necessary documents.'
        }
    ]);
    const [inputText, setInputText] = useState('');
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [entities, setEntities] = useState({});
    const [isComplete, setIsComplete] = useState(false);
    const [extractedData, setExtractedData] = useState(null); // Full session data for final step
    const [documentContent, setDocumentContent] = useState('');
    const [showPreview, setShowPreview] = useState(false);
    const [showSummaryModal, setShowSummaryModal] = useState(false);
    const [actionChoices, setActionChoices] = useState(null);
    const [showActionModal, setShowActionModal] = useState(false);

    // Privacy & Evidence
    const [hasConsented, setHasConsented] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !sessionId) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        formData.append('phoneNumber', '9999999999');

        try {
            const response = await fetch(`http://localhost:8080/api/session/${sessionId}/evidence`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            setExtractedData(data);
            // Auto-refresh logic if needed, or rely on extracting data
        } catch (error) {
            console.error("Upload failed", error);
        } finally {
            setIsUploading(false);
        }
    };

    const handleDeleteCase = async () => {
        if (!window.confirm("Are you sure you want to PERMANENTLY delete this case and all data? This cannot be undone.")) return;

        try {
            await fetch(`http://localhost:8080/api/session/${sessionId}?phoneNumber=9999999999`, {
                method: 'DELETE'
            });
            alert("Case deleted successfully.");
            window.location.reload(); // Reset to start
        } catch (error) {
            console.error("Delete failed", error);
        }
    };

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            alert("Please log in to use the Legal Assistant.");
            navigate('/login');
        }
    }, [navigate]);

    const handleSend = async () => {
        if (!inputText.trim()) return;

        const userMsg = { id: Date.now(), sender: 'user', text: inputText };
        setMessages(prev => [...prev, userMsg]);
        setInputText('');
        setLoading(true);

        try {
            let response;
            if (!sessionId) {
                // First message starts the session
                response = await sessionAPI.start(userMsg.text); // backend uses token for phone number
                setSessionId(response.data.sessionId);
            } else {
                // Subsequent messages are answers
                response = await sessionAPI.answer(sessionId, userMsg.text); // backend uses token
            }

            const data = response.data;
            setEntities(data.extractedEntities || {});
            setExtractedData(data); // Store for final submission

            if (data.actionChoice || data.isActionChoice) {
                const jsonStr = data.nextQuestion.replace("ACTION_CHOICES:", "").trim();
                try {
                    const choices = JSON.parse(jsonStr);
                    setActionChoices(choices);
                    setShowActionModal(true);
                    setMessages(prev => [...prev, {
                        id: Date.now() + 1,
                        sender: 'system',
                        text: "Please select the legal action you would like to pursue from the available options."
                    }]);
                } catch (e) {
                    console.error("Failed to parse action choices", e, jsonStr);
                    handleConfirmAction("General Legal Consultation");
                }
            } else if (data.confirmation || data.isConfirmation) {
                setShowSummaryModal(true);
            } else if (data.complete) {
                setIsComplete(true);
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: data.nextQuestion || "I have gathered all the necessary information. Your document is ready to be generated."
                }]);
            } else if (data.nextQuestion) {
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: data.nextQuestion
                }]);
            }

        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                text: "I'm sorry, I encountered an error connecting to the server. Please try again."
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const generateDocument = async () => {
        try {
            const createResponse = await caseAPI.create({
                initialText: messages[1]?.text || "Chat Session",
                language: 'en',
                entities: extractedData.extractedEntities,
                issueType: extractedData.detectedIntent || 'general_complaint',
                subCategory: extractedData.detectedDomain || 'general'
            });

            const caseRef = createResponse.data;

            const pdfData = {
                ...extractedData.extractedEntities,
                issue_type: extractedData.detectedIntent || 'General Consultation',
                domain: extractedData.detectedDomain,
                description: messages[1]?.text || ""
            };

            const pdfResponse = await documentAPI.generate(pdfData);

            const blob = new Blob([pdfResponse.data], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${caseRef.referenceNumber}.pdf`;
            a.click();

            navigate('/dashboard');

        } catch (err) {
            alert("Error generating document: " + err.message);
        }
    };

    const handleConfirmSummary = async () => {
        setShowSummaryModal(false);
        const userMsg = { id: Date.now(), sender: 'user', text: 'CONFIRM' };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await sessionAPI.answer(sessionId, "CONFIRM");
            const data = response.data;
            setEntities(data.extractedEntities || {});
            setExtractedData(data); // Store for final submission

            if (data.actionChoice || data.isActionChoice) {
                const jsonStr = data.nextQuestion.replace("ACTION_CHOICES:", "").trim();
                try {
                    const choices = JSON.parse(jsonStr);
                    setActionChoices(choices);
                    setShowActionModal(true);
                    setMessages(prev => [...prev, {
                        id: Date.now() + 1,
                        sender: 'system',
                        text: "Please select the legal action you would like to pursue from the available options."
                    }]);
                } catch (e) {
                    console.error("Failed to parse action choices", e, jsonStr);
                    handleConfirmAction("General Legal Consultation");
                }
            } else if (data.complete) {
                setIsComplete(true);
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: data.nextQuestion || "I have gathered all the necessary information. Your document is ready to be generated."
                }]);
            }
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                text: "I'm sorry, an error occurred during confirmation."
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmAction = async (actionTitle) => {
        setShowActionModal(false);
        const userMsg = { id: Date.now(), sender: 'user', text: `Selected: ${actionTitle}` };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await sessionAPI.answer(sessionId, `ACTION: ${actionTitle}`);
            const data = response.data;
            setEntities(data.extractedEntities || {});
            setExtractedData(data);

            if (data.complete) {
                setIsComplete(true);
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: data.nextQuestion || "Your legal documentation is now ready for generation based on your selected action."
                }]);
            }
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                text: "I'm sorry, an error occurred while processing your choice."
            }]);
        } finally {
            setLoading(false);
        }
    };

    // Voice Input Handler
    const handleVoiceInput = async (audioFile) => {
        setLoading(true);
        const processingMsg = { id: Date.now(), sender: 'user', text: '🎤 Voice Input Processing...' };
        setMessages(prev => [...prev, processingMsg]);

        try {
            // Get user details
            const userStr = localStorage.getItem('user');
            const user = userStr ? JSON.parse(userStr) : null;
            const phoneNumber = user?.phoneNumber || '9999999999'; // Fallback only for dev, but really should be logged in

            const formData = new FormData();
            formData.append('audio', audioFile);
            formData.append('transcript', '');
            formData.append('language', 'en-IN');
            formData.append('phoneNumber', phoneNumber);

            let response;
            if (!sessionId) {
                const startRes = await sessionAPI.start("Voice Start");
                const newSessionId = startRes.data.sessionId;
                setSessionId(newSessionId);
                response = await sessionAPI.answerVoice(newSessionId, formData);
            } else {
                response = await sessionAPI.answerVoice(sessionId, formData);
            }

            const data = response.data;
            setMessages(prev => prev.filter(m => m.id !== processingMsg.id));
            setMessages(prev => [...prev, {
                id: Date.now(),
                sender: 'user',
                text: "🎤 [Audio Sent] " + (data.transcript || "")
            }]);

            setEntities(data.extractedEntities || {});
            setExtractedData(data);

            if (data.actionChoice || data.isActionChoice) {
                const jsonStr = data.nextQuestion.replace("ACTION_CHOICES:", "").trim();
                try {
                    const choices = JSON.parse(jsonStr);
                    setActionChoices(choices);
                    setShowActionModal(true);
                    setMessages(prev => [...prev, {
                        id: Date.now() + 1,
                        sender: 'system',
                        text: "Please select the legal action you would like to pursue from the available options."
                    }]);
                } catch (e) {
                    console.error("Failed to parse action choices", e, jsonStr);
                    handleConfirmAction("General Legal Consultation");
                }
            } else if (data.confirmation || data.isConfirmation) {
                setShowSummaryModal(true);
            } else if (data.complete) {
                setIsComplete(true);
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: data.nextQuestion || "I have gathered all the necessary information. Your document is ready to be generated."
                }]);
            } else if (data.nextQuestion) {
                setTimeout(() => {
                    setMessages(prev => [...prev, {
                        id: Date.now() + 1,
                        sender: 'system',
                        text: data.nextQuestion
                    }]);
                }, 500);
            }

        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                text: "Error processing voice input. Please try again."
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="wizard-container">
            <div className="wizard-header">
                <h1>Legal Assistant</h1>
                <div style={{ position: 'absolute', right: '2rem', top: '1rem' }}>
                    <ThemeToggle />
                </div>
            </div>

            <div className="chat-window">
                <div className="messages-area">
                    {messages.map(msg => (
                        <div key={msg.id} className={`message ${msg.sender}`}>
                            {msg.text}
                        </div>
                    ))}
                    {loading && (
                        <div className="typing-indicator">
                            <span>Assistant is typing...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {isComplete ? (
                    <div className="input-area" style={{ justifyContent: 'center' }}>
                        <button className="btn btn-primary" onClick={generateDocument}>
                            📄 Generate Legal Document
                        </button>
                    </div>
                ) : (
                    <div className="input-area">
                        <VoiceRecorder onRecordingComplete={handleVoiceInput} isProcessing={loading} />
                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Type your answer..."
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

            {
                Object.keys(entities).length > 0 && (
                    <div className="entities-panel">
                        <div className="entities-title">Discovered Facts</div>
                        <div className="tag-cloud">
                            {Object.entries(entities)
                                .filter(([_, value]) => value !== 'EXPLICITLY_DENIED')
                                .map(([key, value]) => (
                                    <div key={key} className="data-tag">
                                        <span>{key.replace(/_/g, ' ')}:</span>
                                        <strong>{value}</strong>
                                    </div>
                                ))}
                        </div>

                        {extractedData && extractedData.suggestedSections && (
                            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                                <div className="entities-title" style={{ color: '#ef4444' }}>⚖️ Potential Legal Sections</div>
                                <div style={{
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    padding: '0.8rem',
                                    borderRadius: '8px',
                                    fontSize: '0.9rem',
                                    lineHeight: '1.4',
                                    color: '#fecaca',
                                    border: '1px solid rgba(239, 68, 68, 0.2)'
                                }}>
                                    {extractedData.suggestedSections}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontStyle: 'italic' }}>
                                    ⚠️ Disclaimer: This is AI-generated for guidance only. Consult a lawyer for legal accuracy.
                                </div>
                            </div>
                        )}

                        {extractedData && extractedData.readinessScore !== undefined && (
                            <div style={{ marginTop: '1.5rem' }}>
                                <div className="entities-title">Legal Readiness Score</div>
                                <div className="progress-container" style={{ background: '#334155', borderRadius: '10px', height: '20px', width: '100%', overflow: 'hidden', position: 'relative' }}>
                                    <div style={{
                                        width: `${extractedData.readinessScore}%`,
                                        background: extractedData.readinessScore >= 80 ? '#22c55e' : extractedData.readinessScore >= 50 ? '#eab308' : '#ef4444',
                                        height: '100%',
                                        transition: 'width 0.5s ease-in-out'
                                    }}></div>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                                    <strong>{extractedData.readinessScore}/100</strong>
                                    <span style={{
                                        color: extractedData.readinessScore >= 80 ? '#22c55e' : extractedData.readinessScore >= 50 ? '#eab308' : '#ef4444',
                                        fontWeight: 'bold'
                                    }}>
                                        {extractedData.readinessStatus?.replace('_', ' ')}
                                    </span>
                                </div>
                                {extractedData.readinessScore < 50 && (
                                    <div style={{ fontSize: '0.8rem', color: '#ef4444', marginTop: '5px' }}>
                                        ❌ Case is not legally actionable yet. Please provide more details.
                                    </div>
                                )}
                            </div>
                        )}

                        {extractedData && extractedData.filingGuidance && (
                            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                                <div className="entities-title" style={{ color: '#0ea5e9' }}>📋 Filing Guidance</div>
                                <div style={{ fontSize: '0.9rem', color: '#e2e8f0', background: 'rgba(14, 165, 233, 0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(14, 165, 233, 0.2)' }}>
                                    <div style={{ marginBottom: '0.5rem' }}>
                                        <strong style={{ color: '#7dd3fc' }}>File At:</strong> {extractedData.filingGuidance.authority}
                                    </div>
                                    <div style={{ marginBottom: '0.5rem', fontStyle: 'italic', fontSize: '0.8rem', color: '#94a3b8' }}>
                                        📍 {extractedData.filingGuidance.jurisdiction_hint}
                                    </div>

                                    <div style={{ marginTop: '0.8rem' }}>
                                        <strong style={{ color: '#7dd3fc' }}>Required Enclosures:</strong>
                                        <ul style={{ margin: '0.5rem 0', paddingLeft: '1.2rem' }}>
                                            {extractedData.filingGuidance.enclosures.map((item, idx) => (
                                                <li key={idx}>{item}</li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div style={{ marginTop: '0.8rem' }}>
                                        <strong style={{ color: '#7dd3fc' }}>Next Steps:</strong>
                                        <ol style={{ margin: '0.5rem 0', paddingLeft: '1.2rem' }}>
                                            {extractedData.filingGuidance.next_steps.map((item, idx) => (
                                                <li key={idx}>{item}</li>
                                            ))}
                                        </ol>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )
            }

            {showSummaryModal && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px', minWidth: '400px', maxWidth: '600px',
                        border: '1px solid var(--glass-border)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                    }}>
                        <h2 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Information Summary</h2>
                        <ul style={{ listStyle: 'none', padding: 0, marginBottom: '2rem' }}>
                            {Object.entries(entities)
                                .filter(([_, value]) => value !== 'EXPLICITLY_DENIED')
                                .map(([key, value]) => (
                                    <li key={key} style={{ padding: '0.8rem', background: 'var(--app-bg)', marginBottom: '0.5rem', borderRadius: '6px' }}>
                                        <strong style={{ textTransform: 'capitalize', color: 'var(--primary-color)' }}>{key.replace(/_/g, ' ')}:</strong> {value}
                                    </li>
                                ))}
                        </ul>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" onClick={() => setShowSummaryModal(false)}>Cancel & Keep Editing</button>
                            <button className="btn btn-primary" onClick={handleConfirmSummary}>Yes, I Confirm</button>
                        </div>
                    </div>
                </div>
            )}

            {showActionModal && actionChoices && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px', minWidth: '400px', maxWidth: '800px', width: '90%', maxHeight: '85vh', overflowY: 'auto',
                        border: '1px solid var(--glass-border)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
                    }}>
                        <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-primary)' }}>Select Legal Action</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '1.5rem' }}>
                            {actionChoices.map((choice, idx) => (
                                <div key={idx} style={{ padding: '1.5rem', background: 'var(--app-bg)', borderRadius: '8px', border: '1px solid var(--glass-border)' }}>
                                    <h3 style={{ color: 'var(--primary-color)', marginBottom: '1rem', fontSize: '1.3rem' }}>{choice.title}</h3>

                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                                        <div>
                                            <strong style={{ color: '#22c55e', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem', fontSize: '1rem' }}>✅ Possible Advantages</strong>
                                            <ul style={{ margin: 0, paddingLeft: '0', listStyle: 'none', color: '#e2e8f0', fontSize: '0.9rem' }}>
                                                {choice.pros && choice.pros.map((p, i) => <li key={i} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'start', gap: '0.5rem' }}><span style={{ color: '#22c55e', marginTop: '2px' }}>•</span>{p}</li>)}
                                            </ul>
                                        </div>
                                        <div>
                                            <strong style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.8rem', fontSize: '1rem' }}>⚠️ Potential Risks</strong>
                                            <ul style={{ margin: 0, paddingLeft: '0', listStyle: 'none', color: '#e2e8f0', fontSize: '0.9rem' }}>
                                                {choice.cons && choice.cons.map((c, i) => <li key={i} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'start', gap: '0.5rem' }}><span style={{ color: '#ef4444', marginTop: '2px' }}>•</span>{c}</li>)}
                                            </ul>
                                        </div>
                                    </div>

                                    <button
                                        className="btn btn-primary"
                                        style={{ marginTop: '1.5rem', width: '100%', padding: '1rem', fontWeight: 'bold' }}
                                        onClick={() => handleConfirmAction(choice.title)}>
                                        Proceed with {choice.title}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div >
    );
}

export default CaseWizard;
