import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI, documentAPI, caseAPI } from '../../utils/api';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
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
                response = await sessionAPI.start(userMsg.text);
                setSessionId(response.data.sessionId);
            } else {
                // Subsequent messages are answers
                response = await sessionAPI.answer(sessionId, userMsg.text);
            }

            const data = response.data;
            setEntities(data.extractedEntities || {});
            setExtractedData(data); // Store for final submission

            if (data.nextQuestion) {
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: data.nextQuestion
                }]);
            } else if (data.complete) {
                setIsComplete(true);
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: "I have gathered all the necessary information. Your document is ready to be generated."
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
        // Logic to call document generation (reusing NewCase logic logic)
        // For now, we assume we create the case physically then download
        try {
            // 1. Create the persistent Case Record
            const createResponse = await caseAPI.create({
                initialText: messages[1]?.text || "Chat Session", // The user's first input
                language: 'en', // TODO: Get from NLP
                entities: extractedData.extractedEntities,
                issueType: extractedData.detectedIntent || 'general_complaint',
                subCategory: extractedData.detectedDomain || 'general'
            });

            const caseRef = createResponse.data;

            // 2. Generate PDF using the new Template Engine
            // We merge the extracted entities with metadata
            const pdfData = {
                ...extractedData.extractedEntities,
                issue_type: extractedData.detectedIntent || 'General Consultation',
                domain: extractedData.detectedDomain,
                description: messages[1]?.text || "" // Include original story
            };

            const pdfResponse = await documentAPI.generate(pdfData);

            // Download
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
                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Type your answer..."
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyPress={handleKeyPress}
                            disabled={loading}
                            autoFocus
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
                            {Object.entries(entities).map(([key, value]) => (
                                <div key={key} className="data-tag">
                                    <span>{key.replace(/_/g, ' ')}:</span>
                                    <strong>{value}</strong>
                                </div>
                            ))}
                        </div>

                        {/* Legal Mapping Section */}
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

                        {/* Readiness Score Section */}
                        {extractedData.readinessScore !== undefined && (
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
                                {/* Generate Button Contextual */}
                                {extractedData.readinessScore < 50 && (
                                    <div style={{ fontSize: '0.8rem', color: '#ef4444', marginTop: '5px' }}>
                                        ❌ Case is not legally actionable yet. Please provide more details.
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Filing Guidance Section */}
                        {extractedData.filingGuidance && (
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
        </div >
    );
}

export default CaseWizard;
