import { useState, useRef, useEffect } from 'react';
import './VoiceRecorder.css';

/**
 * VoiceRecorder — uses the browser's native Web Speech API (SpeechRecognition)
 * to transcribe speech in real-time and passes the recognized TEXT string directly
 * to onRecordingComplete. No audio blob, no manual transcript prompt needed.
 */
const VoiceRecorder = ({ onRecordingComplete, isProcessing, language }) => {
    const [isRecording, setIsRecording] = useState(false);
    const [isSupported, setIsSupported] = useState(true);
    const [interimText, setInterimText] = useState('');
    const recognitionRef = useRef(null);
    const finalTranscriptRef = useRef('');

    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setIsSupported(false);
        }
        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.abort();
            }
        };
    }, []);

    const startRecording = () => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        const recognition = new SpeechRecognition();
        // continuous=true lets the user speak in multiple sentences without stopping
        recognition.continuous = true;
        // interimResults=true gives live feedback while they speak
        recognition.interimResults = true;
        // Supports setting exact dialect once detected, otherwise fallback to browser default
        if (language) {
            recognition.lang = `${language}-IN`;
        } else {
            recognition.lang = navigator.language || 'en-IN';
        }
        recognition.maxAlternatives = 1;

        finalTranscriptRef.current = '';
        setInterimText('');

        recognition.onstart = () => setIsRecording(true);

        recognition.onresult = (event) => {
            let interimBuffer = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscriptRef.current += result[0].transcript + ' ';
                } else {
                    interimBuffer += result[0].transcript;
                }
            }
            // Show live interim feedback in the button area
            setInterimText(interimBuffer);
        };

        recognition.onerror = (event) => {
            console.error('SpeechRecognition error:', event.error);
            setIsRecording(false);
            setInterimText('');
            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access in your browser settings.');
            }
        };

        recognition.onend = () => {
            setIsRecording(false);
            setInterimText('');
            const finalText = finalTranscriptRef.current.trim();
            if (finalText) {
                // Pass recognized text directly — treated exactly like typed text
                onRecordingComplete(finalText);
            }
        };

        recognitionRef.current = recognition;
        recognition.start();
    };

    const stopRecording = () => {
        if (recognitionRef.current && isRecording) {
            // Calling stop() triggers onend which fires onRecordingComplete
            recognitionRef.current.stop();
        }
    };

    if (!isSupported) {
        return (
            <div className="voice-recorder" title="Voice input not supported in this browser">
                <button className="btn-record start" disabled>
                    <span className="record-icon">🎤</span>
                    Not Supported
                </button>
            </div>
        );
    }

    return (
        <div className={`voice-recorder ${isRecording ? 'recording' : ''}`}
             title={isRecording ? 'Click to stop and send voice input' : 'Click to start voice input'}>
            {isRecording ? (
                <button className="btn-record stop" onClick={stopRecording}>
                    <span className="record-icon">⏹</span>
                    {interimText ? `"${interimText.substring(0, 20)}…"` : 'Listening…'}
                </button>
            ) : (
                <button className="btn-record start" onClick={startRecording} disabled={isProcessing}>
                    <span className="record-icon">🎤</span>
                    {isProcessing ? 'Processing…' : 'Voice'}
                </button>
            )}
            {isRecording && <div className="recording-pulse"></div>}
        </div>
    );
};

export default VoiceRecorder;
