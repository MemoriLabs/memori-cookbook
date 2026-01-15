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
            Your AI Finance Advisor
            <br />
            <span className="gradient-text">With Perfect Memory</span>
          </h1>
          <p className="hero-description">
            Track your spending patterns, manage budgets, set financial goals, and get
            personalized financial advice. Built on Memori's long-term memory layer for
            context-aware financial coaching.
          </p>
          <div className="hero-cta">
            <button className="btn-primary-lg" onClick={onGetStarted}>
              Start Managing Your Finances
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
              <span className="preview-title">Transaction Log</span>
            </div>
            <div className="preview-content">
              <div className="preview-line">
                <span className="line-label">Coffee Shop:</span>
                <span className="line-value">-$5.50</span>
              </div>
              <div className="preview-line">
                <span className="line-label">Grocery Store:</span>
                <span className="line-value">-$87.32</span>
              </div>
              <div className="preview-line">
                <span className="line-label">Salary:</span>
                <span className="line-value highlight">+$3,500.00 (↑ on track)</span>
              </div>
              <div className="preview-divider"></div>
              <div className="preview-code">
                <code>
                  <span className="kw">Pattern</span> Found:
                  <br />
                  {"    "}Recurring: Netflix $15.99/mo
                  <br />
                  {"    "}Budget: Food $500/mo
                  <br />
                  <br />
                  <span className="kw">Recommendation</span>:
                  <br />
                  {"    "}Reduce dining out by 20%
                  <br />
                  {"    "}to stay within budget
                </code>
              </div>
              <div className="preview-feedback">
                <span className="feedback-icon">✓</span>
                Great! You're 85% within budget this month.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2 className="section-title">Everything You Need for Financial Health</h2>
        <p className="section-subtitle">
          Powered by Memori's memory fabric for AI applications
        </p>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Long-Term Memory</h3>
            <p>
              Every transaction is remembered. Your AI advisor knows your spending history,
              patterns, and what works best for your financial goals.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💰</div>
            <h3>Transaction Tracking</h3>
            <p>
              Log and categorize all your transactions. Automatically identify recurring
              expenses and spending patterns.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Budget Management</h3>
            <p>
              Create budgets and monitor adherence with real-time alerts. Track spending
              by category and get insights on overspending.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Financial Goals</h3>
            <p>
              Set and track financial goals with AI-powered recommendations. Get
              personalized action plans to achieve your objectives.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📈</div>
            <h3>Health Assessments</h3>
            <p>
              Get comprehensive financial health assessments using LangGraph to review
              your financial status and get recommendations.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💡</div>
            <h3>Smart Advice</h3>
            <p>
              Receive specific, actionable financial advice based on your unique spending
              patterns, budgets, and goals.
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
            <p>Tell us your income, financial goals, and risk tolerance.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">2</div>
            <h3>Log Transactions</h3>
            <p>Track all your income and expenses with automatic categorization.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-number">3</div>
            <h3>Get Insights</h3>
            <p>Your AI identifies patterns, manages budgets, and suggests improvements.</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-card">
          <img src={memoriLogo} alt="Memori" className="cta-logo" />
          <h2>Ready to Transform Your Finances?</h2>
          <p>
            Bring your own OpenAI and Memori API keys and start managing your finances with AI-powered advice.
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
