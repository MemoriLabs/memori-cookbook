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
            Master Technical Interviews
            <br />
            <span className="gradient-text">With Perfect Memory</span>
          </h1>
          <p className="hero-description">
            An AI-powered interview prep assistant that remembers your progress,
            identifies weaknesses, and generates personalized problems. Built on
            Memori's long-term memory layer for context-aware coaching.
          </p>
          <div className="hero-cta">
            <button className="btn-primary-lg" onClick={onGetStarted}>
              Start Practicing Now
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
              <span className="preview-title">Practice Session</span>
            </div>
            <div className="preview-content">
              <div className="preview-line">
                <span className="line-label">Problem:</span>
                <span className="line-value">Two Sum (Medium)</span>
              </div>
              <div className="preview-line">
                <span className="line-label">Pattern:</span>
                <span className="line-value">Hash Map, Arrays</span>
              </div>
              <div className="preview-line">
                <span className="line-label">Your Weakness:</span>
                <span className="line-value highlight">Edge cases in DP</span>
              </div>
              <div className="preview-divider"></div>
              <div className="preview-code">
                <code>
                  <span className="kw">def</span>{" "}
                  <span className="fn">two_sum</span>(nums, target):
                  <br />
                  {"    "}seen = {"{"}
                  {"}"}
                  <br />
                  {"    "}
                  <span className="kw">for</span> i, n{" "}
                  <span className="kw">in</span> enumerate(nums):
                  <br />
                  {"        "}
                  <span className="kw">if</span> target - n{" "}
                  <span className="kw">in</span> seen:
                  <br />
                  {"            "}
                  <span className="kw">return</span> [seen[target - n], i]
                  <br />
                  {"        "}seen[n] = i
                </code>
              </div>
              <div className="preview-feedback">
                <span className="feedback-icon">✓</span>
                Optimal O(n) solution. Great improvement from last week!
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2 className="section-title">Everything You Need to Succeed</h2>
        <p className="section-subtitle">
          Powered by Memori's memory fabric for AI applications
        </p>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Long-Term Memory</h3>
            <p>
              Every practice session is remembered. Your AI coach knows your
              history, strengths, and areas for improvement.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Mock Interviews</h3>
            <p>
              Simulate real phone screens and onsite interviews with timed
              sessions and no hints allowed.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Visual Analytics</h3>
            <p>
              Track your progress with charts. See patterns, difficulty
              breakdown, and weekly activity trends.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔄</div>
            <h3>Spaced Repetition</h3>
            <p>
              Review problems at optimal intervals. Build lasting understanding
              with science-backed learning.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🏢</div>
            <h3>Company Prep</h3>
            <p>
              Prepare for Google, Meta, Amazon, and more with company-specific
              problem patterns.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📅</div>
            <h3>AI Study Plans</h3>
            <p>
              Get personalized weekly study plans generated based on your
              profile and weak patterns.
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
            <p>Tell us your target role, experience level, and goals.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>Practice Problems</h3>
            <p>Get AI-generated problems matched to your skill gaps.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Track Progress</h3>
            <p>Your AI remembers everything and adapts to help you grow.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-card">
          <img src={memoriLogo} alt="Memori" className="cta-logo" />
          <h2>Ready to Ace Your Interviews?</h2>
          <p>
            Bring your own OpenAI and Memori API keys and start practicing with AI-powered coaching.
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
