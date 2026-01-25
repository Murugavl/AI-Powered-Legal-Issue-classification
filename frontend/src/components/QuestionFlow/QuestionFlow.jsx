import { useState, useEffect } from 'react';
import { nlpAPI } from '../../utils/api';
import './QuestionFlow.css';

function QuestionFlow({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [userInput, setUserInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [analysisData, setAnalysisData] = useState(null);
  const [collectedData, setCollectedData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const questions = [
    { id: 'initial', text: 'Please describe your legal issue in detail. You can speak or type.' },
  ];

  useEffect(() => {
    if (!('webkitSpeechRecognition' in window)) {
      console.warn("Speech API not supported in this browser");
    }
  }, []);

  const startVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("Browser does not support Speech Recognition");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event) => {
      console.error(event.error);
      setIsListening(false);
      setError('Voice recognition error. Please try again.');
    };

    recognition.onresult = (event) => {
      const transcribedText = event.results[0][0].transcript;
      setTranscript(transcribedText);
      setUserInput(transcribedText);
    };

    recognition.start();
  };

  const stopVoiceInput = () => {
    setIsListening(false);
  };

  const analyzeText = async (text) => {
    setLoading(true);
    setError('');
    try {
      const response = await nlpAPI.analyze(text);
      setAnalysisData(response.data);

      // Collect extracted entities
      const newData = { ...collectedData };
      Object.entries(response.data.entities).forEach(([key, value]) => {
        if (value) {
          newData[key] = value;
        }
      });
      setCollectedData(newData);

      return response.data;
    } catch (err) {
      setError('Failed to analyze text. Please try again.');
      console.error(err);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmVoice = async () => {
    if (!userInput.trim()) {
      setError('Please provide some input first');
      return;
    }

    // First submission - analyze the initial text
    if (currentStep === 0) {
      const analysis = await analyzeText(userInput);
      if (analysis) {
        setCurrentStep(1);
        setUserInput('');
        setTranscript('');
      }
    } else {
      // Answering a follow-up question
      const fieldName = analysisData?.next_question ?
        getFieldNameFromQuestion(analysisData.next_question) : null;

      if (fieldName) {
        setCollectedData({
          ...collectedData,
          [fieldName]: userInput,
        });
      }

      // Re-analyze with updated data
      const combinedText = Object.values({ ...collectedData, [fieldName]: userInput }).join(' ');
      const analysis = await analyzeText(combinedText);

      if (analysis && !analysis.next_question) {
        // All required fields collected
        handleComplete();
      } else {
        setUserInput('');
        setTranscript('');
      }
    }
  };

  const getFieldNameFromQuestion = (question) => {
    if (question.includes('name')) return 'name';
    if (question.includes('date') || question.includes('when')) return 'date';
    if (question.includes('location') || question.includes('where')) return 'location';
    if (question.includes('accused') || question.includes('responsible')) return 'accused';
    if (question.includes('stolen')) return 'stolen_items';
    if (question.includes('injur')) return 'injuries';
    if (question.includes('property')) return 'property_details';
    return 'description';
  };

  const handleComplete = () => {
    onComplete({
      text: Object.values(collectedData).join(' '),
      entities: analysisData?.entities || {},
      issueType: analysisData?.entities?.issue_type || 'general',
      language: analysisData?.language || 'en',
      completeness: analysisData?.completeness || {},
    });
  };

  const getCurrentQuestion = () => {
    if (currentStep === 0) {
      return questions[0].text;
    }
    return analysisData?.next_question || 'Please confirm all details are correct.';
  };

  const getProgress = () => {
    if (!analysisData) return 0;
    return Math.round((analysisData.confidence || 0) * 100);
  };

  return (
    <div className="question-flow">
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${getProgress()}%` }}></div>
        <span className="progress-text">{getProgress()}% Complete</span>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="question-card">
        <h2 className="question-title">
          {loading ? 'Analyzing...' : getCurrentQuestion()}
        </h2>

        {analysisData && analysisData.entities && (
          <div className="collected-info">
            <h3>Information Collected:</h3>
            <div className="info-grid">
              {Object.entries(analysisData.completeness || {}).map(([field, isComplete]) => (
                <div key={field} className={`info-item ${isComplete ? 'complete' : 'incomplete'}`}>
                  <span className="info-label">{field.replace('_', ' ')}:</span>
                  <span className="info-value">
                    {analysisData.entities[field] || 'Missing'}
                  </span>
                  {isComplete && <span className="check-mark">✓</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="input-section">
          <textarea
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder={isListening ? "Listening..." : "Type your answer or use voice input..."}
            disabled={isListening || loading}
            rows="5"
          />

          <div className="button-group">
            <button
              onClick={isListening ? stopVoiceInput : startVoiceInput}
              className={`btn ${isListening ? 'btn-danger' : 'btn-secondary'}`}
              disabled={loading}
            >
              {isListening ? '🛑 Stop Listening' : '🎙️ Voice Input'}
            </button>

            <button
              onClick={handleConfirmVoice}
              className="btn btn-primary"
              disabled={!userInput.trim() || loading}
            >
              {loading ? 'Processing...' : 'Confirm & Continue'}
            </button>
          </div>
        </div>

        {transcript && (
          <div className="transcript-box">
            <p><strong>Voice Transcript:</strong> {transcript}</p>
            <p className="transcript-hint">Please review and edit if needed, then confirm.</p>
          </div>
        )}
      </div>

      {analysisData && (
        <div className="analysis-info">
          <p><strong>Issue Type:</strong> {analysisData.entities?.issue_type || 'Analyzing...'}</p>
          <p><strong>Language:</strong> {analysisData.language || 'Unknown'}</p>
        </div>
      )}
    </div>
  );
}

export default QuestionFlow;
