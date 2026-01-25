import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEffect } from 'react';
import './Home.css';

function Home() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="home">
      <div className="home-header">
        <div className="header-content">
          <h1>Legal Document Assistant</h1>
          <p>Voice-First Legal Documentation for Everyone</p>
        </div>
      </div>

      <div className="home-content">
        <section className="hero">
          <h2>Access Justice in Your Language</h2>
          <p className="hero-subtitle">
            Create legally structured, authority-ready documents through simple voice or text input
          </p>
          <div className="cta-buttons">
            <button onClick={() => navigate('/register')} className="btn btn-primary btn-large">
              Get Started Free
            </button>
            <button onClick={() => navigate('/login')} className="btn btn-secondary btn-large">
              Login
            </button>
          </div>
        </section>

        <section className="features">
          <h3>How It Works</h3>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🎙️</div>
              <h4>1. Speak or Type</h4>
              <p>Describe your legal issue in your own language using voice or text input</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">💬</div>
              <h4>2. Interactive Q&A</h4>
              <p>Answer simple questions one at a time. We guide you through the process</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">✓</div>
              <h4>3. Review & Confirm</h4>
              <p>Check all details are correct before we generate your document</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">📄</div>
              <h4>4. Download Document</h4>
              <p>Get your bilingual, authority-ready document with reference number</p>
            </div>
          </div>
        </section>

        <section className="benefits">
          <h3>Why Use Our Platform?</h3>
          <div className="benefits-list">
            <div className="benefit-item">
              <span className="benefit-icon">🌍</span>
              <div>
                <h5>Multilingual Support</h5>
                <p>English, Hindi, Tamil, Telugu, Bengali, Marathi and more</p>
              </div>
            </div>

            <div className="benefit-item">
              <span className="benefit-icon">🔒</span>
              <div>
                <h5>Secure & Private</h5>
                <p>Your data is encrypted and stored securely</p>
              </div>
            </div>

            <div className="benefit-item">
              <span className="benefit-icon">⚡</span>
              <div>
                <h5>Fast & Easy</h5>
                <p>Create documents in minutes, not hours</p>
              </div>
            </div>

            <div className="benefit-item">
              <span className="benefit-icon">📱</span>
              <div>
                <h5>Mobile Friendly</h5>
                <p>Works on any device - phone, tablet, or computer</p>
              </div>
            </div>
          </div>
        </section>

        <section className="disclaimer-section">
          <div className="disclaimer-box">
            <h4>⚠️ Important Disclaimer</h4>
            <p>
              This application provides document templates and assistance only. It does NOT
              provide legal advice. All generated documents should be reviewed by a qualified
              legal professional before submission to authorities.
            </p>
          </div>
        </section>
      </div>

      <footer className="home-footer">
        <p>Built with ❤️ for accessible justice in India</p>
      </footer>
    </div>
  );
}

export default Home;
