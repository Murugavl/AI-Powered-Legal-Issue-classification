import { useState, useEffect } from 'react';

function App() {
  const [text, setText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [language, setLanguage] = useState('unknown');
  const [entities, setEntities] = useState(null);
  const [alert, setAlert] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!('webkitSpeechRecognition' in window)) {
      console.warn("Speech API not supported in this browser");
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Browser does not support Speech Recognition");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN'; // Defaulting to English (India), could toggle

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event) => console.error(event.error);

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setText(prev => prev + ' ' + transcript);
    };

    recognition.start();
  };

  const verifyDocument = async () => {
    setLoading(true);
    setAlert(null);
    try {
      // Step 1: Frontend Risk Check
      if (text.toLowerCase().includes('kill') || text.toLowerCase().includes('suicide') || text.toLowerCase().includes('bomb')) {
        setAlert("HIGH RISK DETECTED: CALL 112 IMMEDIATELY");
        setLoading(false);
        return;
      }

      // Step 2: NLP Analysis (Extraction)
      const nlpResponse = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      let extractedEntities = {};
      if (nlpResponse.ok) {
        const data = await nlpResponse.json();
        setLanguage(data.language);
        setEntities(data.entities);
        extractedEntities = data.entities;
      } else {
        console.error("NLP Service Failed");
        extractedEntities = { name: null, date: null, location: null, accused: null };
      }

      // Step 3: Backend Verification Loop
      const verifyResponse = await fetch('http://localhost:8080/api/documents/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          entities: extractedEntities
        })
      });

      if (verifyResponse.ok) {
        const verifyData = await verifyResponse.json();
        if (verifyData.status === "INCOMPLETE") {
          // Show alerts for missing fields?
          // For now, we rely on the visual missing fields in the entities-grid.
          console.log("Missing Fields:", verifyData.missingFields);
        }
        if (verifyData.alert) {
          setAlert(verifyData.alert);
        }
      }

    } catch (e) {
      console.error("Verification Error:", e);
      if (e.message && e.message.includes('Failed to fetch')) {
        setAlert("Backend Service Unavailable (Is Java running?). Showing NLP results only.");
      }
    }
    setLoading(false);
  };

  const translateText = async (targetLang) => {
    try {
      const response = await fetch('http://localhost:8000/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, target_language: targetLang })
      });
      if (response.ok) {
        const data = await response.json();
        // Show in a customized alert or modal in production
        alert(`Translation (${targetLang}):\n${data.translated_text}`);
      }
    } catch (e) {
      console.error("Translation Error:", e);
      alert("Translation Service Unavailable");
    }
  };

  const generatePdf = async () => {
    // Only allow if no alert?
    if (alert && alert.includes("HIGH RISK")) return; // Block high risk

    try {
      const response = await fetch('http://localhost:8080/api/documents/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          englishText: text,
          localText: text + " \n(Translated Content Pending)"
        })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "legal_doc.pdf";
        a.click();
      } else {
        alert("Backend failed to generate PDF. Setup Java Backend.");
      }
    } catch (e) {
      console.error(e);
      alert("Backend Unreachable: Cannot generate PDF.");
    }
  };

  return (
    <div className="App">
      <h1>Document Readiness</h1>
      <p style={{ color: '#94a3b8', marginBottom: '2rem' }}>Voice-First Legal Documentation Assistant</p>

      {alert && (
        <div className="alert-box">
          <h2>⚠️ {alert}</h2>
          <button className="danger" onClick={() => window.open('tel:112')}>Call 112 Now</button>
        </div>
      )}

      <div className="glass-card">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe the incident... (e.g. 'My name is Rahul, I was at Chennai on 12/05/2025...')"
        />

        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button onClick={toggleListening} className={isListening ? 'danger' : 'primary'}>
            {isListening ? '🛑 Stop Listening' : '🎙️ Start Voice Input'}
          </button>
          <button onClick={verifyDocument} disabled={!text}>
            🔍 Verify & Analyze
          </button>
        </div>
      </div>

      {entities && (
        <div className="glass-card">
          <h2>Analysis Result</h2>
          <p>Language Detected: <span style={{ color: 'var(--primary-color)' }}>{language}</span></p>

          <div className="entities-grid">
            <div className="entity-item">
              <span className="entity-label">Name</span>
              <div className="entity-value">{entities.name || 'MISSING'}</div>
            </div>
            <div className="entity-item">
              <span className="entity-label">Date</span>
              <div className="entity-value">{entities.date || 'MISSING'}</div>
            </div>
            <div className="entity-item">
              <span className="entity-label">Location</span>
              <div className="entity-value">{entities.location || 'MISSING'}</div>
            </div>
            <div className="entity-item">
              <span className="entity-label">Accused</span>
              <div className="entity-value">{entities.accused || 'MISSING'}</div>
            </div>
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button onClick={() => translateText('en')} style={{ background: '#334155' }}>Translate to English</button>
            <button onClick={() => translateText('ta')} style={{ background: '#334155' }}>Translate to Tamil</button>
            <button onClick={() => translateText('hi')} style={{ background: '#334155' }}>Translate to Hindi</button>

            <button className="primary" onClick={generatePdf}>
              📄 Generate Bilingual PDF
            </button>
          </div>
        </div>
      )}

      <div className="disclaimer">
        DISCLAIMER: This system is for preliminary data collection only. <br />
        NOT LEGAL ADVICE. Generated documents must be verified by a legal professional.
      </div>
    </div>
  );
}

export default App;
