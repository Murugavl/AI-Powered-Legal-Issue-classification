import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { sessionAPI, documentAPI, caseAPI } from '../../utils/api';
import ThemeToggle from '../ThemeToggle/ThemeToggle';
import VoiceRecorder from './VoiceRecorder';
import './CaseWizard.css';

// ============================================================
// Stage Labels for 9-Stage Workflow Indicator
// ============================================================
const STAGES = [
    { id: 'intake', label: 'Issue Intake', icon: '📝' },
    { id: 'readiness', label: 'Readiness Check', icon: '✅' },
    { id: 'action_id', label: 'Legal Actions', icon: '⚖️' },
    { id: 'action_explain', label: 'Action Details', icon: '📋' },
    { id: 'action_confirm', label: 'Confirm Action', icon: '🎯' },
    { id: 'data_collect', label: 'Data Collection', icon: '📊' },
    { id: 'gen_document', label: 'Document Generation', icon: '📄' },
    { id: 'draft_mgmt', label: 'Draft Management', icon: '💾' },
    { id: 'completed', label: 'Complete', icon: '🏁' },
];

function getCurrentStageIndex(stage, nextStep, isComplete) {
    if (isComplete || stage === 'completed') return 8;
    if (nextStep === 'generate_document') return 6;
    if (stage === 'action_id' || nextStep === 'ask_action_choice') return 2;
    if (stage === 'readiness' || nextStep === 'ask_confirmation') return 1;
    return 0;
}

function CaseWizard() {
    const navigate = useNavigate();
    const location = useLocation();
    const [messages, setMessages] = useState([
        {
            id: 'greeting',
            sender: 'system',
            text: '⚖️ Welcome to Satta Vizhi – Your AI Indian Legal Assistant\n\nI will guide you through a 9-stage process to help you understand your legal rights and generate professionally formatted legal documents.\n\nPlease describe your legal issue in your own words. The more detail you provide, the better I can help you.'
        }
    ]);
    const [inputText, setInputText] = useState('');
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [entities, setEntities] = useState({});
    const [isComplete, setIsComplete] = useState(false);
    const [extractedData, setExtractedData] = useState(null);
    const [documentContent, setDocumentContent] = useState('');
    const [showPreview, setShowPreview] = useState(false);
    const [showSummaryModal, setShowSummaryModal] = useState(false);
    const [actionChoices, setActionChoices] = useState(null);
    const [showActionModal, setShowActionModal] = useState(false);
    const [selectedActionForConfirm, setSelectedActionForConfirm] = useState(null);
    const [showActionConfirmModal, setShowActionConfirmModal] = useState(false);
    const [draftCaseId, setDraftCaseId] = useState(null);
    const draftCaseIdRef = useRef(null);

    // Document format selection
    const [showFormatModal, setShowFormatModal] = useState(false);
    const [bilingualDocument, setBilingualDocument] = useState(null);
    const [isGeneratingDoc, setIsGeneratingDoc] = useState(false);

    // Stage tracking
    const [currentStage, setCurrentStage] = useState('intake');
    const [currentNextStep, setCurrentNextStep] = useState('ask_question');
    const [readinessScore, setReadinessScore] = useState(0);

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
        } catch (error) {
            console.error("Upload failed", error);
        } finally {
            setIsUploading(false);
        }
    };

    // Auto-save draft
    useEffect(() => {
        if (!sessionId) return;
        const autoSaveDraft = async () => {
            try {
                let issue = extractedData?.detectedIntent || 'general_complaint';
                if (issue.length > 50) issue = issue.substring(0, 50);
                let subCat = extractedData?.detectedDomain || 'general';
                if (subCat.length > 50) subCat = subCat.substring(0, 50);

                const payload = {
                    initialText: messages[1]?.text || "Chat Session",
                    language: 'en',
                    entities: entities,
                    issueType: issue,
                    subCategory: subCat,
                    sessionId: sessionId
                };

                if (!draftCaseIdRef.current) {
                    const res = await caseAPI.create(payload);
                    draftCaseIdRef.current = res.data.caseId;
                    setDraftCaseId(res.data.caseId);
                } else {
                    await caseAPI.update(draftCaseIdRef.current, payload);
                }
            } catch (err) {
                console.error("Auto-save draft failed", err);
            }
        };
        autoSaveDraft();
    }, [sessionId, entities, extractedData]);

    const handleDeleteCase = async () => {
        if (!window.confirm("Are you sure you want to PERMANENTLY delete this session and all its data? This cannot be undone.")) return;
        setLoading(true);
        try {
            await sessionAPI.deleteSession(sessionId);
            alert("Draft deleted successfully.");
            window.location.reload();
        } catch (error) {
            console.error("Delete failed", error);
        } finally {
            setLoading(false);
        }
    };

    const messagesEndRef = useRef(null);
    const scrollToBottom = () => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); };
    useEffect(() => { scrollToBottom(); }, [messages]);

    useEffect(() => {
        const token = sessionStorage.getItem('token');
        if (!token) {
            alert("Please log in to use the Legal Assistant.");
            navigate('/login');
        }
    }, [navigate]);

    // Load draft from URL
    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const urlCaseId = queryParams.get('caseId');

        if (urlCaseId && !draftCaseIdRef.current) {
            const loadDraft = async () => {
                try {
                    setLoading(true);
                    const caseRes = await caseAPI.getById(urlCaseId);
                    const caseData = caseRes.data;

                    draftCaseIdRef.current = caseData.caseId;
                    setDraftCaseId(caseData.caseId);

                    const extractedEntitiesObj = {};
                    if (caseData.entities) {
                        for (const [k, v] of Object.entries(caseData.entities)) {
                            extractedEntitiesObj[k] = v.value;
                        }
                    }
                    setEntities(extractedEntitiesObj);

                    setExtractedData({
                        detectedIntent: caseData.issueType,
                        detectedDomain: caseData.subCategory,
                        extractedEntities: extractedEntitiesObj
                    });

                    if (caseData.sessionId) {
                        setSessionId(caseData.sessionId);
                        const historyRes = await sessionAPI.getHistory(caseData.sessionId);
                        if (historyRes.data && historyRes.data.length > 0) {
                            setMessages([
                                {
                                    id: 'greeting',
                                    sender: 'system',
                                    text: '⚖️ Welcome back! Resuming your draft case.\n\nI am your AI Indian Legal Assistant. Here is your conversation history so far:'
                                },
                                ...historyRes.data
                            ]);
                        }
                    }
                } catch (err) {
                    console.error("Failed to load draft", err);
                } finally {
                    setLoading(false);
                }
            };
            loadDraft();
        }
    }, [location.search]);

    // ============================================================
    // Process API Response → Update State
    // ============================================================
    const processApiResponse = (data) => {
        console.log('[CaseWizard] API Response:', {
            stage: data.detectedDomain,
            score: data.readinessScore,
            is_confirmation: data.confirmation || data.isConfirmation,
            is_action_choice: data.actionChoice || data.isActionChoice,
            is_complete: data.complete,
            nextQuestion_preview: (data.nextQuestion || '').slice(0, 80)
        });

        // Always sync state
        setEntities(data.extractedEntities || {});
        setExtractedData(data);
        setReadinessScore(data.readinessScore || 0);

        const stage = data.detectedDomain || '';
        const nextQ = data.nextQuestion || '';

        // Sync current_stage for progress bar
        if (stage) setCurrentStage(stage);

        // Determine if there's a bilingual document
        if (data.bilingualDocument) {
            setBilingualDocument(data.bilingualDocument);
        }

        // --- Primary routing: use stage from server ---

        // COMPLETED: Document has been generated
        if (data.complete || stage === 'completed') {
            setIsComplete(true);
            setCurrentStage('completed');
            if (data.bilingualDocument) setBilingualDocument(data.bilingualDocument);
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                text: nextQ || "✅ Your legal document is ready!\n\nClick '📄 Download Legal Document' to generate your PDF."
            }]);
            return;
        }

        // ACTION CHOICE: Server wants us to show legal action options
        const isActionChoice = !!(data.actionChoice || data.isActionChoice || stage === 'action_choice');
        if (isActionChoice && nextQ.includes('ACTION_CHOICES:')) {
            const jsonStr = nextQ.replace('ACTION_CHOICES:', '').trim();
            try {
                const choices = JSON.parse(jsonStr);
                setActionChoices(choices);
                setShowActionModal(true);
                setCurrentStage('action_id');
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: '⚖️ Based on your case, I have identified the following legal actions. Please review and choose one:'
                }]);
            } catch (e) {
                console.error('Failed to parse action choices JSON:', e, jsonStr);
                // Fallback — treat as regular message
                setMessages(prev => [...prev, { id: Date.now() + 1, sender: 'system', text: nextQ }]);
            }
            return;
        }

        // CONFIRMATION: Server wants user to review collected facts
        const isConfirmation = !!(data.confirmation || data.isConfirmation || stage === 'confirmation');
        if (isConfirmation) {
            setShowSummaryModal(true);
            setCurrentStage('readiness');
            // Also add the summary text as a chat message so user can see it
            if (nextQ && !nextQ.includes('ACTION_CHOICES:')) {
                setMessages(prev => [...prev, {
                    id: Date.now() + 1,
                    sender: 'system',
                    text: nextQ
                }]);
            }
            return;
        }

        // REGULAR QUESTION or action confirm prompt: show in chat
        if (nextQ) {
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                sender: 'system',
                text: nextQ
            }]);
        }
    };


    // ============================================================
    // Handle Send Message
    // ============================================================
    const handleSend = async () => {
        if (!inputText.trim()) return;

        const userMsg = { id: Date.now(), sender: 'user', text: inputText };
        setMessages(prev => [...prev, userMsg]);
        setInputText('');
        setLoading(true);

        try {
            let response;
            if (!sessionId) {
                response = await sessionAPI.start(userMsg.text);
                setSessionId(response.data.sessionId);
            } else {
                response = await sessionAPI.answer(sessionId, userMsg.text);
            }
            processApiResponse(response.data);
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

    // ============================================================
    // Stage 5: Action Confirm (pre-confirm selected action)
    // ============================================================
    const handleSelectAction = (choice) => {
        setSelectedActionForConfirm(choice);
        setShowActionModal(false);
        setShowActionConfirmModal(true);
    };

    const handleConfirmActionFinal = async () => {
        if (!selectedActionForConfirm) return;
        setShowActionConfirmModal(false);
        await handleConfirmAction(selectedActionForConfirm.title, selectedActionForConfirm);
    };

    const handleConfirmAction = async (actionTitle, choice) => {
        setShowActionModal(false);
        setShowActionConfirmModal(false);

        const userMsg = {
            id: Date.now(),
            sender: 'user',
            text: `✅ Selected Action: ${actionTitle}`
        };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await sessionAPI.answer(sessionId, `ACTION: ${actionTitle}`);
            // Use the shared handler — it handles action_confirm prompt, questions, or completion
            processApiResponse(response.data);
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

    // ============================================================
    // Stage 2: Confirm Summary
    // ============================================================
    const handleConfirmSummary = async () => {
        setShowSummaryModal(false);
        setCurrentStage('action_id');
        const userMsg = { id: Date.now(), sender: 'user', text: 'CONFIRM' };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const response = await sessionAPI.answer(sessionId, "CONFIRM");
            processApiResponse(response.data);
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

    // ============================================================
    // Stage 7: Document Generation
    // ============================================================
    const generateDocument = async (format) => {
        setShowFormatModal(false);
        setIsGeneratingDoc(true);

        try {
            let issue = extractedData?.detectedIntent || 'general_complaint';
            if (issue.length > 50) issue = issue.substring(0, 50);
            let subCat = extractedData?.detectedDomain || 'general';
            if (subCat.length > 50) subCat = subCat.substring(0, 50);

            const payload = {
                initialText: messages[1]?.text || 'Chat Session',
                language: 'en',
                entities: extractedData?.extractedEntities || entities,
                issueType: issue,
                subCategory: subCat,
                sessionId: sessionId
            };

            // Create or update case record
            let caseRef;
            try {
                if (!draftCaseIdRef.current && !draftCaseId) {
                    const createResponse = await caseAPI.create(payload);
                    caseRef = createResponse.data;
                    draftCaseIdRef.current = caseRef.caseId;
                    setDraftCaseId(caseRef.caseId);
                } else {
                    const updateResponse = await caseAPI.update(draftCaseIdRef.current || draftCaseId, payload);
                    caseRef = updateResponse.data;
                }
            } catch (caseErr) {
                console.warn('Case save failed (non-fatal):', caseErr.message);
                caseRef = {};
            }

            const refNum = caseRef?.referenceNumber || `LDA-${Date.now()}`;

            // Build bilingual payload from stored bilingual document
            if (bilingualDocument) {
                const bilingualPayload = {
                    user_language_content: bilingualDocument.user_language_content || bilingualDocument.english_content || '',
                    english_content: bilingualDocument.english_content || '',
                    user_language: bilingualDocument.user_language || 'en',
                    reference_number: refNum,
                    document_type: bilingualDocument.document_type || 'legal_document',
                    readiness_score: bilingualDocument.readiness_score || 100,
                    metadata: {
                        'Case ID': caseRef?.caseId || 'N/A',
                        'Issue Type': issue,
                        'Selected Action': bilingualDocument.selected_action || '',
                        'Generated On': new Date().toLocaleDateString('en-IN')
                    }
                };

                const pdfResponse = await documentAPI.generateBilingual(bilingualPayload);
                const blob = new Blob([pdfResponse.data], { type: 'application/pdf' });
                const blobUrl = window.URL.createObjectURL(blob);

                if (format === 'open') {
                    window.open(blobUrl, '_blank');
                } else if (format === 'pdf') {
                    const a = document.createElement('a');
                    a.href = blobUrl;
                    a.download = `legal_document_${refNum}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(blobUrl);
                } else if (format === 'docx') {
                    // Generate plain-text DOCX-compatible content
                    const docContent = `${bilingualDocument.english_content || ''}`;
                    const docBlob = new Blob([docContent], { type: 'text/plain' });
                    const a = document.createElement('a');
                    a.href = window.URL.createObjectURL(docBlob);
                    a.download = `legal_document_${refNum}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }

                setMessages(prev => [...prev, {
                    id: Date.now(),
                    sender: 'system',
                    text: `✅ Document ${format === 'open' ? 'opened' : 'downloaded'} successfully!\n\n📋 Reference: ${refNum}\n⚠️ Important: Review the document with a qualified lawyer before submission.`
                }]);

            } else {
                // Fallback: simple PDF
                const pdfData = {
                    ...(extractedData?.extractedEntities || entities),
                    issue_type: issue,
                    domain: subCat,
                    description: messages[1]?.text || ''
                };
                const pdfResponse = await documentAPI.generate(pdfData);
                const blob = new Blob([pdfResponse.data], { type: 'application/pdf' });
                const blobUrl = window.URL.createObjectURL(blob);

                if (format === 'open') {
                    window.open(blobUrl, '_blank');
                } else {
                    const a = document.createElement('a');
                    a.href = blobUrl;
                    a.download = `legal_document_${refNum}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(blobUrl);
                }
            }

        } catch (err) {
            console.error('Document generation error:', err);
            setMessages(prev => [...prev, {
                id: Date.now(),
                sender: 'system',
                text: `⚠️ Document generation failed: ${err.message || 'Please try again.'}`
            }]);
        } finally {
            setIsGeneratingDoc(false);
        }
    };

    // ============================================================
    // Voice Input Handler
    // ============================================================
    const handleVoiceInput = async (audioFile) => {
        setLoading(true);
        const processingMsg = { id: Date.now(), sender: 'user', text: '🎤 Voice Input Processing...' };
        setMessages(prev => [...prev, processingMsg]);

        try {
            const userStr = sessionStorage.getItem('user');
            const user = userStr ? JSON.parse(userStr) : null;
            const phoneNumber = user?.phoneNumber || '9999999999';

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
            processApiResponse(data);

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

    const stageIdx = getCurrentStageIndex(currentStage, currentNextStep, isComplete);

    return (
        <div className="wizard-container">
            {/* Header */}
            <div className="wizard-header">
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <h1>⚖️ Satta Vizhi – AI Legal Assistant</h1>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
                        9-Stage Indian Legal Workflow Orchestrator
                    </span>
                </div>
                <div style={{ position: 'absolute', right: '2rem', top: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {sessionId && (
                        <button onClick={handleDeleteCase} className="btn" style={{ padding: '0.5rem 1rem', background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', borderRadius: '4px', cursor: 'pointer' }}>
                            🗑️ Delete Draft
                        </button>
                    )}
                    <ThemeToggle />
                </div>
            </div>

            {/* 9-Stage Progress Bar */}
            <div style={{
                display: 'flex',
                overflowX: 'auto',
                padding: '0.75rem 1.5rem',
                background: 'var(--card-bg)',
                borderBottom: '1px solid var(--glass-border)',
                gap: '0.25rem'
            }}>
                {STAGES.map((stage, idx) => (
                    <div key={stage.id} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        flex: '0 0 auto'
                    }}>
                        <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '0.25rem'
                        }}>
                            <div style={{
                                width: '32px',
                                height: '32px',
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '1rem',
                                background: idx < stageIdx ? '#22c55e' :
                                    idx === stageIdx ? 'var(--primary-color)' :
                                        'var(--app-bg)',
                                border: idx <= stageIdx ? 'none' : '2px solid var(--glass-border)',
                                transition: 'all 0.3s ease',
                                boxShadow: idx === stageIdx ? '0 0 12px rgba(99,102,241,0.5)' : 'none'
                            }}>
                                {idx < stageIdx ? '✓' : stage.icon}
                            </div>
                            <span style={{
                                fontSize: '0.6rem',
                                color: idx <= stageIdx ? 'var(--text-primary)' : 'var(--text-muted)',
                                fontWeight: idx === stageIdx ? '700' : '400',
                                whiteSpace: 'nowrap',
                                maxWidth: '70px',
                                textAlign: 'center',
                                lineHeight: '1.2'
                            }}>
                                {stage.label}
                            </span>
                        </div>
                        {idx < STAGES.length - 1 && (
                            <div style={{
                                width: '24px',
                                height: '2px',
                                background: idx < stageIdx ? '#22c55e' : 'var(--glass-border)',
                                marginBottom: '14px',
                                transition: 'background 0.3s ease'
                            }} />
                        )}
                    </div>
                ))}
            </div>

            {/* Main Chat Window */}
            <div className="chat-window">
                <div className="messages-area">
                    {messages.map(msg => (
                        <div key={msg.id} className={`message ${msg.sender}`}>
                            <span style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</span>
                        </div>
                    ))}
                    {loading && (
                        <div className="typing-indicator">
                            <span>Legal Assistant is analyzing...</span>
                        </div>
                    )}
                    {isGeneratingDoc && (
                        <div className="typing-indicator">
                            <span>📄 Generating your legal document...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                {isComplete ? (
                    <div style={{ padding: '1.5rem', background: 'var(--card-bg)', borderTop: '1px solid var(--glass-border)' }}>
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(34,197,94,0.1) 0%, rgba(99,102,241,0.1) 100%)',
                            border: '1px solid rgba(34,197,94,0.3)',
                            borderRadius: '12px',
                            padding: '1.5rem',
                            textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🏛️</div>
                            <h3 style={{ color: 'var(--text-primary)', margin: '0 0 0.25rem', fontSize: '1.1rem' }}>
                                Your Legal Document is Ready
                            </h3>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0 0 1.25rem' }}>
                                Choose how you'd like to access your document — open it in browser, download as PDF, or get a text copy.
                            </p>
                            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                                <button
                                    className="btn"
                                    style={{
                                        padding: '0.75rem 1.25rem',
                                        background: 'rgba(99,102,241,0.15)',
                                        border: '1px solid rgba(99,102,241,0.4)',
                                        color: 'var(--primary-color)',
                                        borderRadius: '8px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem',
                                        display: 'flex', alignItems: 'center', gap: '0.5rem'
                                    }}
                                    onClick={() => generateDocument('open')}
                                    disabled={isGeneratingDoc}
                                    title="Open PDF in a new browser tab"
                                >
                                    🔍 Open Document
                                </button>
                                <button
                                    className="btn btn-primary"
                                    style={{
                                        padding: '0.75rem 1.25rem',
                                        fontWeight: '600',
                                        fontSize: '0.9rem',
                                        display: 'flex', alignItems: 'center', gap: '0.5rem'
                                    }}
                                    onClick={() => generateDocument('pdf')}
                                    disabled={isGeneratingDoc}
                                    title="Download as PDF file"
                                >
                                    📥 Download PDF
                                </button>
                                <button
                                    className="btn"
                                    style={{
                                        padding: '0.75rem 1.25rem',
                                        background: 'rgba(14,165,233,0.15)',
                                        border: '1px solid rgba(14,165,233,0.4)',
                                        color: '#38bdf8',
                                        borderRadius: '8px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem',
                                        display: 'flex', alignItems: 'center', gap: '0.5rem'
                                    }}
                                    onClick={() => generateDocument('docx')}
                                    disabled={isGeneratingDoc}
                                    title="Download as text/Word file"
                                >
                                    📝 Download Word (.txt)
                                </button>
                                <button
                                    className="btn"
                                    style={{
                                        padding: '0.75rem 1.25rem',
                                        background: 'transparent',
                                        border: '1px solid var(--glass-border)',
                                        color: 'var(--text-muted)',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem',
                                        display: 'flex', alignItems: 'center', gap: '0.5rem'
                                    }}
                                    onClick={() => navigate('/dashboard')}
                                >
                                    📊 Dashboard
                                </button>
                            </div>
                            {isGeneratingDoc && (
                                <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                    ⏳ Generating document, please wait...
                                </div>
                            )}
                            <p style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                ⚠️ This AI-generated document is for guidance only. Please review with a qualified Indian lawyer before filing.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="input-area">
                        <VoiceRecorder onRecordingComplete={handleVoiceInput} isProcessing={loading} />
                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Type your answer... (Press Enter to send)"
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


            {/* Right Panel: Discovered Facts + Legal Insights */}
            {Object.keys(entities).length > 0 && (
                <div className="entities-panel">
                    <div className="entities-title">📋 Discovered Facts</div>
                    <div className="tag-cloud">
                        {Object.entries(entities)
                            .filter(([_, value]) => value !== 'EXPLICITLY_DENIED' && value !== 'NOT_AVAILABLE')
                            .map(([key, value]) => (
                                <div key={key} className="data-tag">
                                    <span>{key.replace(/_/g, ' ')}:</span>
                                    <strong>{value}</strong>
                                </div>
                            ))}
                    </div>

                    {/* Suggested Legal Sections */}
                    {extractedData?.suggestedSections && (
                        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                            <div className="entities-title" style={{ color: '#ef4444' }}>⚖️ Potential Legal Sections</div>
                            <div style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                padding: '0.8rem',
                                borderRadius: '8px',
                                fontSize: '0.85rem',
                                lineHeight: '1.6',
                                color: '#fecaca',
                                border: '1px solid rgba(239, 68, 68, 0.2)'
                            }}>
                                {extractedData.suggestedSections.split(' | ').map((s, i) => (
                                    <div key={i}>• {s}</div>
                                ))}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.4rem', fontStyle: 'italic' }}>
                                ⚠️ AI-generated guidance only. Consult a lawyer for accuracy.
                            </div>
                        </div>
                    )}

                    {/* Readiness Score */}
                    {readinessScore > 0 && (
                        <div style={{ marginTop: '1.5rem' }}>
                            <div className="entities-title">📊 Legal Readiness Score</div>
                            <div style={{ background: '#334155', borderRadius: '10px', height: '20px', width: '100%', overflow: 'hidden' }}>
                                <div style={{
                                    width: `${readinessScore}%`,
                                    background: readinessScore >= 80 ? '#22c55e' : readinessScore >= 50 ? '#eab308' : '#ef4444',
                                    height: '100%',
                                    transition: 'width 0.5s ease-in-out'
                                }} />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                                <strong>{readinessScore}/100</strong>
                                <span style={{ color: readinessScore >= 80 ? '#22c55e' : readinessScore >= 50 ? '#eab308' : '#ef4444', fontWeight: 'bold' }}>
                                    {readinessScore >= 100 ? 'LEGALLY READY' : readinessScore >= 80 ? 'NEARLY READY' : readinessScore >= 50 ? 'PARTIALLY READY' : 'NOT READY'}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Filing Guidance */}
                    {extractedData?.filingGuidance && extractedData.filingGuidance.authority && (
                        <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1rem' }}>
                            <div className="entities-title" style={{ color: '#0ea5e9' }}>📑 Filing Guidance</div>
                            <div style={{ fontSize: '0.85rem', color: '#e2e8f0', background: 'rgba(14, 165, 233, 0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(14, 165, 233, 0.2)' }}>
                                <div style={{ marginBottom: '0.5rem' }}>
                                    <strong style={{ color: '#7dd3fc' }}>File At:</strong><br />{extractedData.filingGuidance.authority}
                                </div>
                                <div style={{ marginBottom: '0.5rem', fontSize: '0.8rem', color: '#94a3b8', fontStyle: 'italic' }}>
                                    📍 {extractedData.filingGuidance.jurisdiction_hint}
                                </div>
                                <div style={{ marginTop: '0.8rem' }}>
                                    <strong style={{ color: '#7dd3fc' }}>Required Documents:</strong>
                                    <ul style={{ margin: '0.4rem 0', paddingLeft: '1.2rem' }}>
                                        {(extractedData.filingGuidance.enclosures || []).map((item, idx) => (
                                            <li key={idx} style={{ marginBottom: '0.25rem' }}>{item}</li>
                                        ))}
                                    </ul>
                                </div>
                                <div style={{ marginTop: '0.8rem' }}>
                                    <strong style={{ color: '#7dd3fc' }}>Next Steps:</strong>
                                    <ol style={{ margin: '0.4rem 0', paddingLeft: '1.2rem' }}>
                                        {(extractedData.filingGuidance.next_steps || []).map((item, idx) => (
                                            <li key={idx} style={{ marginBottom: '0.25rem' }}>{item}</li>
                                        ))}
                                    </ol>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ============================================================ */}
            {/* STAGE 2 MODAL: Summary Confirmation */}
            {/* ============================================================ */}
            {showSummaryModal && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', display: 'flex',
                    justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px',
                        minWidth: '450px', maxWidth: '650px', border: '1px solid var(--glass-border)',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)', maxHeight: '80vh', overflowY: 'auto'
                    }}>
                        <h2 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            ✅ Stage 2 – Legal Readiness Evaluation
                        </h2>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                            Please review the information I have collected. Once confirmed, I will identify applicable legal actions.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, marginBottom: '2rem' }}>
                            {Object.entries(entities)
                                .filter(([_, value]) => value !== 'EXPLICITLY_DENIED' && value !== 'NOT_AVAILABLE')
                                .map(([key, value]) => (
                                    <li key={key} style={{ padding: '0.7rem', background: 'var(--app-bg)', marginBottom: '0.5rem', borderRadius: '6px', borderLeft: '3px solid var(--primary-color)' }}>
                                        <strong style={{ color: 'var(--primary-color)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.05em' }}>
                                            {key.replace(/_/g, ' ')}
                                        </strong>
                                        <div style={{ color: 'var(--text-primary)', marginTop: '0.25rem' }}>{value}</div>
                                    </li>
                                ))}
                        </ul>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" onClick={() => setShowSummaryModal(false)} style={{ padding: '0.75rem 1.5rem' }}>
                                ✏️ Edit & Keep Refining
                            </button>
                            <button className="btn btn-primary" onClick={handleConfirmSummary} style={{ padding: '0.75rem 1.5rem' }}>
                                ✅ Confirm & Proceed to Legal Analysis
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ============================================================ */}
            {/* STAGE 3 & 4 MODAL: Legal Action Identification + Explanation */}
            {/* ============================================================ */}
            {showActionModal && actionChoices && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', display: 'flex',
                    justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px',
                        minWidth: '450px', maxWidth: '900px', width: '95%', maxHeight: '90vh', overflowY: 'auto',
                        border: '1px solid var(--glass-border)', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)'
                    }}>
                        <h2 style={{ marginBottom: '0.25rem', color: 'var(--text-primary)' }}>
                            ⚖️ Stages 3 & 4 – Legal Action Identification & Explanation
                        </h2>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                            Based on your case, here are the available legal actions. Review each option carefully before selecting.
                        </p>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '1.5rem' }}>
                            {actionChoices.map((choice, idx) => (
                                <div key={idx} style={{
                                    padding: '1.5rem', background: 'var(--app-bg)', borderRadius: '10px',
                                    border: '1px solid var(--glass-border)', position: 'relative'
                                }}>
                                    {/* Risk Badge */}
                                    {choice.risk_level && (
                                        <div style={{
                                            position: 'absolute', top: '1rem', right: '1rem',
                                            padding: '0.25rem 0.75rem', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '700',
                                            background: choice.risk_level === 'HIGH' ? 'rgba(239,68,68,0.2)' :
                                                choice.risk_level === 'MEDIUM' ? 'rgba(234,179,8,0.2)' : 'rgba(34,197,94,0.2)',
                                            color: choice.risk_level === 'HIGH' ? '#ef4444' :
                                                choice.risk_level === 'MEDIUM' ? '#eab308' : '#22c55e',
                                            border: `1px solid ${choice.risk_level === 'HIGH' ? '#ef4444' : choice.risk_level === 'MEDIUM' ? '#eab308' : '#22c55e'}`
                                        }}>
                                            ⚡ {choice.risk_level} RISK
                                        </div>
                                    )}

                                    <h3 style={{ color: 'var(--primary-color)', marginBottom: '0.5rem', fontSize: '1.2rem', paddingRight: '6rem' }}>
                                        {choice.title || choice.action_name}
                                    </h3>

                                    {/* Legal Basis */}
                                    {choice.legal_basis && (
                                        <div style={{ marginBottom: '0.75rem', padding: '0.5rem', background: 'rgba(139,92,246,0.1)', borderRadius: '6px', border: '1px solid rgba(139,92,246,0.2)' }}>
                                            <strong style={{ color: '#a78bfa', fontSize: '0.85rem' }}>⚖️ Legal Basis: </strong>
                                            <span style={{ color: '#ddd6fe', fontSize: '0.85rem' }}>{choice.legal_basis}</span>
                                        </div>
                                    )}

                                    {/* What this action does */}
                                    {choice.what_this_action_does && (
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <strong style={{ color: '#7dd3fc', fontSize: '0.9rem' }}>📌 What This Does:</strong>
                                            <p style={{ color: '#e2e8f0', fontSize: '0.9rem', marginTop: '0.25rem', lineHeight: '1.5' }}>{choice.what_this_action_does}</p>
                                        </div>
                                    )}

                                    {/* Procedure overview */}
                                    {choice.procedure_overview && Array.isArray(choice.procedure_overview) && (
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <strong style={{ color: '#7dd3fc', fontSize: '0.9rem' }}>📋 Procedure:</strong>
                                            <ol style={{ margin: '0.25rem 0', paddingLeft: '1.5rem', color: '#e2e8f0', fontSize: '0.85rem' }}>
                                                {choice.procedure_overview.map((step, i) => (
                                                    <li key={i} style={{ marginBottom: '0.25rem' }}>{step}</li>
                                                ))}
                                            </ol>
                                        </div>
                                    )}

                                    {/* Time estimate */}
                                    {choice.time_estimate && (
                                        <div style={{ marginBottom: '0.75rem' }}>
                                            <strong style={{ color: '#7dd3fc', fontSize: '0.9rem' }}>⏱️ Time Estimate: </strong>
                                            <span style={{ color: '#e2e8f0', fontSize: '0.9rem' }}>{choice.time_estimate}</span>
                                        </div>
                                    )}

                                    {/* What happens if not taken */}
                                    {choice.what_happens_if_not_taken && (
                                        <div style={{ marginBottom: '0.75rem', padding: '0.5rem', background: 'rgba(239,68,68,0.08)', borderRadius: '6px', border: '1px solid rgba(239,68,68,0.15)' }}>
                                            <strong style={{ color: '#fca5a5', fontSize: '0.85rem' }}>⚠️ If Not Taken: </strong>
                                            <span style={{ color: '#fecaca', fontSize: '0.85rem' }}>{choice.what_happens_if_not_taken}</span>
                                        </div>
                                    )}

                                    {/* Pros & Cons */}
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '0.75rem' }}>
                                        <div>
                                            <strong style={{ color: '#22c55e', fontSize: '0.9rem' }}>✅ Advantages</strong>
                                            <ul style={{ margin: '0.25rem 0', paddingLeft: '0', listStyle: 'none', fontSize: '0.85rem' }}>
                                                {(choice.pros || []).map((p, i) => (
                                                    <li key={i} style={{ marginBottom: '0.3rem', display: 'flex', gap: '0.4rem', color: '#e2e8f0' }}>
                                                        <span style={{ color: '#22c55e' }}>•</span>{p}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                        <div>
                                            <strong style={{ color: '#ef4444', fontSize: '0.9rem' }}>⚠️ Risks</strong>
                                            <ul style={{ margin: '0.25rem 0', paddingLeft: '0', listStyle: 'none', fontSize: '0.85rem' }}>
                                                {(choice.cons || []).map((c, i) => (
                                                    <li key={i} style={{ marginBottom: '0.3rem', display: 'flex', gap: '0.4rem', color: '#e2e8f0' }}>
                                                        <span style={{ color: '#ef4444' }}>•</span>{c}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>

                                    <button
                                        className="btn btn-primary"
                                        style={{ marginTop: '1.25rem', width: '100%', padding: '0.85rem', fontWeight: '600' }}
                                        onClick={() => handleSelectAction(choice)}
                                    >
                                        🎯 Proceed with "{choice.title || choice.action_name}"
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* ============================================================ */}
            {/* STAGE 5 MODAL: Confirm Selected Action */}
            {/* ============================================================ */}
            {showActionConfirmModal && selectedActionForConfirm && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', display: 'flex',
                    justifyContent: 'center', alignItems: 'center', zIndex: 1001
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2rem', borderRadius: '12px',
                        minWidth: '400px', maxWidth: '550px', border: '1px solid var(--glass-border)',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)'
                    }}>
                        <h2 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>
                            🎯 Stage 5 – Confirm Your Action Selection
                        </h2>
                        <div style={{ padding: '1rem', background: 'var(--app-bg)', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid var(--glass-border)' }}>
                            <div style={{ fontWeight: '600', color: 'var(--primary-color)', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
                                {selectedActionForConfirm.title || selectedActionForConfirm.action_name}
                            </div>
                            {selectedActionForConfirm.legal_basis && (
                                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                    ⚖️ {selectedActionForConfirm.legal_basis}
                                </div>
                            )}
                        </div>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                            Are you sure you want to proceed with this legal action? I will now prepare the necessary document for you.
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" onClick={() => {
                                setShowActionConfirmModal(false);
                                setShowActionModal(true);
                            }} style={{ padding: '0.75rem 1.5rem' }}>
                                ← Back to Options
                            </button>
                            <button className="btn btn-primary" onClick={handleConfirmActionFinal} style={{ padding: '0.75rem 1.5rem' }}>
                                ✅ Yes, Proceed
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* ============================================================ */}
            {/* STAGE 7 MODAL: Document Format Selection */}
            {/* ============================================================ */}
            {showFormatModal && (
                <div className="modal-overlay" style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', display: 'flex',
                    justifyContent: 'center', alignItems: 'center', zIndex: 1000
                }}>
                    <div className="modal-content" style={{
                        background: 'var(--card-bg)', padding: '2.5rem', borderRadius: '12px',
                        minWidth: '400px', maxWidth: '560px', border: '1px solid var(--glass-border)',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)'
                    }}>
                        <h2 style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                            📄 Stage 7 – Download Legal Document
                        </h2>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', fontSize: '0.9rem' }}>
                            Your legally formatted document is ready. Choose your preferred format:
                        </p>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
                            {/* Bilingual PDF */}
                            <button
                                onClick={() => generateDocument('bilingual')}
                                style={{
                                    padding: '1.25rem', borderRadius: '10px', border: '2px solid var(--primary-color)',
                                    background: 'rgba(99,102,241,0.1)', cursor: 'pointer', textAlign: 'left',
                                    transition: 'transform 0.2s'
                                }}
                                onMouseEnter={e => e.target.style.transform = 'scale(1.02)'}
                                onMouseLeave={e => e.target.style.transform = 'scale(1)'}
                            >
                                <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>📄 Bilingual PDF</div>
                                <div style={{ color: 'var(--text-primary)', fontWeight: '600' }}>PDF – Your Language + English</div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                    Includes document in your language and English version for official submission. ✅ Recommended
                                </div>
                            </button>

                            {/* Simple PDF */}
                            <button
                                onClick={() => generateDocument('simple')}
                                style={{
                                    padding: '1.25rem', borderRadius: '10px', border: '1px solid var(--glass-border)',
                                    background: 'var(--app-bg)', cursor: 'pointer', textAlign: 'left',
                                    transition: 'transform 0.2s'
                                }}
                                onMouseEnter={e => e.target.style.transform = 'scale(1.02)'}
                                onMouseLeave={e => e.target.style.transform = 'scale(1)'}
                            >
                                <div style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>📃 Simple PDF</div>
                                <div style={{ color: 'var(--text-primary)', fontWeight: '600' }}>PDF – English Only</div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                    Standard English format for direct submission.
                                </div>
                            </button>
                        </div>

                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.5rem', padding: '0.75rem', background: 'rgba(234,179,8,0.05)', borderRadius: '6px', border: '1px solid rgba(234,179,8,0.15)' }}>
                            ⚠️ <strong>Disclaimer:</strong> This document is AI-generated based on information you provided. Please review with a qualified legal professional before official submission.
                        </div>

                        <button className="btn btn-secondary" onClick={() => setShowFormatModal(false)} style={{ width: '100%', padding: '0.75rem' }}>
                            ← Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default CaseWizard;
