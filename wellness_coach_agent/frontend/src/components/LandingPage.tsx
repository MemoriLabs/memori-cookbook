import React from "react";
import memoriLogo from "../../assets/Memori_Logo.png";

type Props = {
  onGetStarted: () => void;
};

function LandingPage({ onGetStarted }: Props) {
  return (
    <div className="landing-page">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-brand">
          <img src={memoriLogo} alt="Memori" className="nav-logo" />
        </div>
        <div className="nav-links">
          <a
            href="https://memorilabs.ai/docs/"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-link"
          >
            Docs
          </a>
          <a
            href="https://github.com/MemoriLabs/Memori"
            target="_blank"
            rel="noopener noreferrer"
            className="nav-link"
          >
            GitHub
          </a>
          <button className="btn-cta-small" onClick={onGetStarted}>
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-dot"></span>
            Powered by Memori Memory Fabric
          </div>
          <h1 className="hero-title">
            Your AI Wellness Companion
            <br />
            <span className="gradient-text">With Perfect Memory</span>
          </h1>
          <p className="hero-description">
            Track your daily habits (sleep, exercise, nutrition, mood) over time,
            identify correlations, and get personalized wellness plans. Built on
            Memori's long-term memory layer for context-aware coaching.
          </p>
          <div className="hero-cta">
            <button className="btn-primary-lg" onClick={onGetStarted}>
              Start Your Wellness Journey
            </button>
            <a
              href="https://memorilabs.ai/"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary-lg"
            >
              Try Memori for Yourself →
            </a>
          </div>
          <div className="hero-stats">
            <div className="stat">
              <span className="stat-value">∞</span>
              <span className="stat-label">Memory Retention</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <span className="stat-value">AI</span>
              <span className="stat-label">Personalized</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <span className="stat-value">BYOK</span>
              <span className="stat-label">Your API Keys</span>
            </div>
          </div>
        </div>
        <div className="hero-visual">
          <div className="code-preview">
            <div className="preview-header">
              <span className="dot red"></span>
              <span className="dot yellow"></span>
              <span className="dot green"></span>
              <span className="preview-title">Daily Wellness Log</span>
            </div>
            <div className="preview-content">
              <div className="preview-line">
                <span className="line-label">Sleep:</span>
                <span className="line-value">8.5 hours (Quality: 8/10)</span>
              </div>
              <div className="preview-line">
                <span className="line-label">Exercise:</span>
                <span className="line-value">Running, 30 min</span>
              </div>
              <div className="preview-line">
                <span className="line-label">Mood:</span>
                <span className="line-value highlight">8/10 (↑ from last week)</span>
              </div>
              <div className="preview-divider"></div>
              <div className="preview-code">
                <code>
                  <span className="kw">Correlation</span> Found:
                  <br />
                  {"    "}Sleep hours ↑ → Mood score ↑
                  <br />
                  {"    "}Strength: <span className="fn">0.82</span>
                  <br />
                  <br />
                  <span className="kw">Recommendation</span>:
                  <br />
                  {"    "}Aim for 8+ hours sleep
                  <br />
                  {"    "}to improve mood stability
                </code>
              </div>
              <div className="preview-feedback">
                <span className="feedback-icon">✓</span>
                Great progress! Your sleep-mood correlation is strong.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2 className="section-title">Everything You Need for Wellness</h2>
        <p className="section-subtitle">
          Powered by Memori's memory fabric for AI applications
        </p>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Long-Term Memory</h3>
            <p>
              Every habit log is remembered. Your AI coach knows your history,
              patterns, and what works best for you.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Correlation Analysis</h3>
            <p>
              Automatically identify relationships between sleep, exercise,
              nutrition, and mood to understand what drives your wellness.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📅</div>
            <h3>Daily Habit Tracking</h3>
            <p>
              Log sleep, exercise, nutrition, and mood metrics daily.
              Track trends and patterns over time.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Personalized Plans</h3>
            <p>
              Get AI-generated wellness plans tailored to your goals,
              habits, and identified weak areas.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📈</div>
            <h3>Weekly Check-Ins</h3>
            <p>
              Conduct weekly assessments with LangGraph to review progress,
              identify trends, and get recommendations.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💡</div>
            <h3>Smart Interventions</h3>
            <p>
              Receive specific, actionable interventions based on your
              unique patterns and correlations.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-section">
        <h2 className="section-title">How It Works</h2>
        <div className="steps-container">
          <div className="step">
            <div className="step-number">1</div>
            <h3>Set Your Profile</h3>
            <p>Tell us your wellness goals, activity level, and preferences.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>Log Daily Habits</h3>
            <p>Track sleep, exercise, nutrition, and mood every day.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Get Insights</h3>
            <p>Your AI identifies correlations and suggests personalized interventions.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-card">
          <img src={memoriLogo} alt="Memori" className="cta-logo" />
          <h2>Ready to Transform Your Wellness?</h2>
          <p>
            Bring your own OpenAI and Memori API keys and start tracking with AI-powered coaching.
          </p>
          <div className="cta-buttons">
            <button className="btn-primary-lg" onClick={onGetStarted}>
              Launch Dashboard
            </button>
            <a
              href="https://memorilabs.ai/"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-outline-lg"
            >
              Learn More About Memori
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <img src={memoriLogo} alt="Memori" className="footer-logo" />
            <p>The memory fabric for enterprise AI</p>
          </div>
          <div className="footer-links">
            <a
              href="https://memorilabs.ai/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Home
            </a>
            <a
              href="https://memorilabs.ai/docs/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Docs
            </a>
            <a
              href="https://github.com/MemoriLabs/Memori"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
          </div>
        </div>
        <div className="footer-bottom">
          <p>© 2025 Memori Labs. Built with Memori Memory Fabric.</p>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
