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
      {/* Navbar Placeholder */}
      <nav className="navbar glass-card">
        <div className="logo-container">
          <img src="/satta_vizhi_logo.png" alt="Satta Vizhi Logo" className="logo-img" />
          <span className="logo-text text-gradient">Satta Vizhi</span>
        </div>
        <div className="nav-links">
          <button onClick={() => navigate('/login')} className="btn btn-secondary">Login</button>
          <button onClick={() => navigate('/register')} className="btn btn-primary">Get Started</button>
        </div>
      </nav>

      <div className="home-content section-padding">
        <section className="hero">
          <div className="hero-text">
            <h1 className="hero-title">
              Legal Documentation <br />
              <span className="text-gradient">Simplified for Everyone</span>
            </h1>
            <p className="hero-subtitle">
              Transform your voice into authority-ready legal documents in minutes.
              Multilingual, secure, and accessible justice powered by AI.
            </p>
            <div className="cta-buttons">
              <button onClick={() => navigate('/register')} className="btn btn-primary btn-lg">
                Start Your Case Free
              </button>
              <button onClick={() => navigate('/login')} className="btn btn-secondary btn-lg">
                Existing User
              </button>
            </div>
          </div>
          <div className="hero-visual">
            {/* Abstract visual element */}
            <div className="glowing-orb"></div>
          </div>
        </section>

        <section className="features-section">
          <h2 className="section-title">How It Works</h2>
          <div className="features-grid">
            <div className="feature-card glass-card">
              <div className="icon-wrapper">🎙️</div>
              <h3>1. Speak Naturally</h3>
              <p>Describe your issue in your own language using voice or text. No legal jargon needed.</p>
            </div>

            <div className="feature-card glass-card">
              <div className="icon-wrapper">🤖</div>
              <h3>2. AI Analysis</h3>
              <p>Our intelligent system extracts key details like dates, names, and locations automatically.</p>
            </div>

            <div className="feature-card glass-card">
              <div className="icon-wrapper">📄</div>
              <h3>3. Instant Document</h3>
              <p>Receive a perfectly formatted, legally structured document ready for submission.</p>
            </div>
          </div>
        </section>

        <section className="trust-section">
          <div className="trust-grid">
            <div className="trust-item">
              <h3>10+</h3>
              <p>Languages Supported</p>
            </div>
            <div className="trust-item">
              <h3>Encryption</h3>
              <p>Enterprise Grade</p>
            </div>
            <div className="trust-item">
              <h3>24/7</h3>
              <p>Instant Access</p>
            </div>
          </div>
        </section>
      </div>

      <footer className="footer section-padding">
        <div className="footer-content">
          <p className="copyright">© 2026 JurisAI. All rights reserved.</p>
          <p className="disclaimer-text">
            Disclaimer: This platform provides automated document templates and is not a substitute for professional legal advice.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default Home;
