import React, { useEffect, useState } from "react";
import { CandidateProfile, ProblemMetadata, ProgressMessage } from "../types";
import ProfileTab from "./ProfileTab";
import PracticeTab from "./PracticeTab";
import ProgressTab from "./ProgressTab";
import HistoryTab from "./HistoryTab";
import AnalyticsTab from "./AnalyticsTab";
import MockInterviewTab from "./MockInterviewTab";
import StudyPlanTab from "./StudyPlanTab";
import memoriLogo from "../../assets/Memori_Logo.png";

const API_BASE = "https://technical-interview-prep-agent-production.up.railway.app/docs";

type TabKey = "profile" | "practice" | "progress" | "history" | "analytics" | "mock" | "study";

const defaultProfile: CandidateProfile = {
  name: "",
  target_role: "",
  experience_level: "Student",
  primary_language: "Python",
  target_companies: [],
  main_goal: "",
  timeframe: ""
};

type Props = {
  onBackToLanding: () => void;
};

function Dashboard({ onBackToLanding }: Props) {
  const [userId, setUserId] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("profile");
  const [profile, setProfile] = useState<CandidateProfile>(defaultProfile);
  const [hasProfile, setHasProfile] = useState(false);
  const [problem, setProblem] = useState<ProblemMetadata | null>(null);
  const [solutionCode, setSolutionCode] = useState("");
  const [hints, setHints] = useState<string[]>([]);
  const [evaluationMarkdown, setEvaluationMarkdown] = useState("");
  const [progressMessages, setProgressMessages] = useState<ProgressMessage[]>([]);
  const [loadingInit, setLoadingInit] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // User-provided API keys (required)
  const [userOpenaiKey, setUserOpenaiKey] = useState("");
  const [userMemoriKey, setUserMemoriKey] = useState("");
  const [showKeysModal, setShowKeysModal] = useState(false);

  // Check if both API keys are configured
  const hasApiKeys = userOpenaiKey.trim().length > 0 && userMemoriKey.trim().length > 0;

  // Sidebar collapsed state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (!userId.trim() || !hasApiKeys) {
      return;
    }

    const init = async () => {
      setLoadingInit(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/init`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            userId: userId.trim(),
            openaiKey: userOpenaiKey.trim(),
            memoriKey: userMemoriKey.trim(),
          })
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail ?? "Failed to initialize session");
        }
        const data = await res.json();
        if (data.profile) {
          setProfile(data.profile);
          setHasProfile(true);
        } else {
          setProfile(defaultProfile);
          setHasProfile(false);
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
      } finally {
        setLoadingInit(false);
      }
    };

    void init();
  }, [userId, hasApiKeys]);

  const handleSaveApiKeys = () => {
    if (!userOpenaiKey.trim() || !userMemoriKey.trim()) {
      setError("Please enter both OpenAI and Memori API keys.");
      return;
    }
    setShowKeysModal(false);
    setError(null);
  };

  const resetPracticeState = () => {
    setProblem(null);
    setSolutionCode("");
    setHints([]);
    setEvaluationMarkdown("");
  };

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="sidebar-header">
          <img src={memoriLogo} alt="Memori" className="sidebar-logo" />
          {!sidebarCollapsed && <span className="sidebar-title">Interview Prep</span>}
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            {sidebarCollapsed ? "→" : "←"}
          </button>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === "profile" ? "active" : ""}`}
            onClick={() => setActiveTab("profile")}
          >
            <span className="nav-icon">👤</span>
            {!sidebarCollapsed && <span>Profile & Goals</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "practice" ? "active" : ""}`}
            onClick={() => setActiveTab("practice")}
            disabled={!hasProfile || !userId.trim()}
          >
            <span className="nav-icon">🧠</span>
            {!sidebarCollapsed && <span>Practice</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "mock" ? "active" : ""}`}
            onClick={() => setActiveTab("mock")}
            disabled={!hasProfile || !userId.trim()}
          >
            <span className="nav-icon">🎯</span>
            {!sidebarCollapsed && <span>Mock Interview</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "history" ? "active" : ""}`}
            onClick={() => setActiveTab("history")}
            disabled={!userId.trim()}
          >
            <span className="nav-icon">📚</span>
            {!sidebarCollapsed && <span>History</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "analytics" ? "active" : ""}`}
            onClick={() => setActiveTab("analytics")}
            disabled={!userId.trim()}
          >
            <span className="nav-icon">📊</span>
            {!sidebarCollapsed && <span>Analytics</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "study" ? "active" : ""}`}
            onClick={() => setActiveTab("study")}
            disabled={!hasProfile || !userId.trim()}
          >
            <span className="nav-icon">📅</span>
            {!sidebarCollapsed && <span>Study Plan</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "progress" ? "active" : ""}`}
            onClick={() => setActiveTab("progress")}
            disabled={!userId.trim()}
          >
            <span className="nav-icon">💬</span>
            {!sidebarCollapsed && <span>Ask Coach</span>}
          </button>
        </nav>

        <div className="sidebar-footer">
          <button className="nav-item" onClick={() => setShowKeysModal(true)}>
            <span className="nav-icon">🔑</span>
            {!sidebarCollapsed && <span>API Keys</span>}
          </button>
          <button className="nav-item" onClick={onBackToLanding}>
            <span className="nav-icon">←</span>
            {!sidebarCollapsed && <span>Back to Home</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="dashboard-main">
        {/* Top Bar */}
        <header className="dashboard-header">
          <div className="header-left">
            <div className="user-input-wrapper">
              <label htmlFor="user-id-dash">User ID</label>
              <input
                id="user-id-dash"
                type="text"
                value={userId}
                placeholder="Enter your handle..."
                onChange={(e) => setUserId(e.target.value)}
                className="user-id-field"
              />
            </div>
          </div>
          <div className="header-right">
            {hasApiKeys ? (
              <div className="status-badge success">
                <span className="status-dot"></span>
                API Keys configured
              </div>
            ) : (
              <button className="btn-primary" onClick={() => setShowKeysModal(true)}>
                🔑 Set API Keys
              </button>
            )}
          </div>
        </header>

        {/* Notifications */}
        {!hasApiKeys && (
          <div className="notification warning">
            <span className="notification-icon">🔑</span>
            Please set your OpenAI and Memori API keys to use the app.
            <button className="btn-small" onClick={() => setShowKeysModal(true)} style={{ marginLeft: 'auto' }}>
              Set API Keys
            </button>
          </div>
        )}
        {loadingInit && (
          <div className="notification info">
            <span className="notification-icon">⏳</span>
            Initializing your session...
          </div>
        )}
        {error && (
          <div className="notification error">
            <span className="notification-icon">⚠️</span>
            {error}
            <button className="notification-close" onClick={() => setError(null)}>
              ×
            </button>
          </div>
        )}

        {/* Tab Content */}
        <div className="dashboard-content">
          {activeTab === "profile" && (
            <ProfileTab
              apiBase={API_BASE}
              userId={userId.trim()}
              profile={profile}
              setProfile={setProfile}
              setHasProfile={setHasProfile}
              onProfileUpdated={resetPracticeState}
              openaiKey={userOpenaiKey.trim()}
              memoriKey={userMemoriKey.trim()}
            />
          )}

          {activeTab === "practice" && userId.trim() && (
            <PracticeTab
              apiBase={API_BASE}
              userId={userId.trim()}
              profile={profile}
              problem={problem}
              setProblem={setProblem}
              solutionCode={solutionCode}
              setSolutionCode={setSolutionCode}
              hints={hints}
              setHints={setHints}
              evaluationMarkdown={evaluationMarkdown}
              setEvaluationMarkdown={setEvaluationMarkdown}
              openaiKey={userOpenaiKey.trim()}
              memoriKey={userMemoriKey.trim()}
            />
          )}

          {activeTab === "progress" && userId.trim() && (
            <ProgressTab
              apiBase={API_BASE}
              userId={userId.trim()}
              messages={progressMessages}
              setMessages={setProgressMessages}
              openaiKey={userOpenaiKey.trim()}
              memoriKey={userMemoriKey.trim()}
            />
          )}

          {activeTab === "history" && userId.trim() && (
            <HistoryTab
              apiBase={API_BASE}
              userId={userId.trim()}
            />
          )}

          {activeTab === "analytics" && userId.trim() && (
            <AnalyticsTab
              apiBase={API_BASE}
              userId={userId.trim()}
            />
          )}

          {activeTab === "mock" && userId.trim() && (
            <MockInterviewTab
              apiBase={API_BASE}
              userId={userId.trim()}
              profile={profile}
              openaiKey={userOpenaiKey.trim()}
              memoriKey={userMemoriKey.trim()}
            />
          )}

          {activeTab === "study" && userId.trim() && (
            <StudyPlanTab
              apiBase={API_BASE}
              userId={userId.trim()}
              profile={profile}
              openaiKey={userOpenaiKey.trim()}
              memoriKey={userMemoriKey.trim()}
            />
          )}
        </div>
      </main>

      {/* API Keys Modal */}
      {showKeysModal && (
        <div className="modal-overlay" onClick={() => setShowKeysModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🔑 API Keys Required</h2>
              <button
                className="modal-close"
                onClick={() => setShowKeysModal(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-description">
                Enter your OpenAI and Memori API keys to use the app. Your keys are stored locally
                and never sent to our servers.
              </p>
              <div className="form-group">
                <label htmlFor="modal-openai">OpenAI API Key</label>
                <input
                  id="modal-openai"
                  type="password"
                  value={userOpenaiKey}
                  placeholder="sk-..."
                  onChange={(e) => setUserOpenaiKey(e.target.value)}
                />
                <p className="subtle" style={{ marginTop: '4px', marginBottom: '16px' }}>
                  Get your key from{" "}
                  <a
                    href="https://platform.openai.com/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    platform.openai.com/api-keys
                  </a>
                </p>
              </div>
              <div className="form-group">
                <label htmlFor="modal-memori">Memori API Key</label>
                <input
                  id="modal-memori"
                  type="password"
                  value={userMemoriKey}
                  placeholder="Your Memori API key..."
                  onChange={(e) => setUserMemoriKey(e.target.value)}
                />
                <p className="subtle" style={{ marginTop: '4px' }}>
                  Get your key from{" "}
                  <a
                    href="https://memorilabs.ai"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    memorilabs.ai
                  </a>
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-primary" onClick={handleSaveApiKeys}>
                Save API Keys
              </button>
              <button
                className="btn-ghost"
                onClick={() => setShowKeysModal(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
