import React, { useEffect, useState } from "react";
import { WellnessProfile, DailyHabitEntry } from "../types";
import ProfileTab from "./ProfileTab";
import DailyLogTab from "./DailyLogTab";
import AnalyticsTab from "./AnalyticsTab";
import WellnessPlanTab from "./WellnessPlanTab";
import CheckInTab from "./CheckInTab";
import memoriLogo from "../../assets/Memori_Logo.png";

const API_BASE = "http://localhost:8000";

type TabKey = "profile" | "daily" | "analytics" | "plan" | "checkin";

const defaultProfile: WellnessProfile = {
  name: "",
  age: undefined,
  gender: undefined,
  primary_goals: [],
  health_conditions: [],
  activity_level: "Moderate",
  time_commitment: "30 minutes/day",
  preferences: [],
};

type Props = {
  onBackToLanding: () => void;
};

function Dashboard({ onBackToLanding }: Props) {
  const [userId, setUserId] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("profile");
  const [profile, setProfile] = useState<WellnessProfile>(defaultProfile);
  const [hasProfile, setHasProfile] = useState(false);
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

  const handleSaveProfile = async (updatedProfile: WellnessProfile) => {
    if (!userId.trim() || !hasApiKeys) {
      setError("Please set User ID and API keys first.");
      return;
    }

    setError(null);
    try {
      const res = await fetch(`${API_BASE}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: userId.trim(),
          profile: updatedProfile,
          openaiKey: userOpenaiKey.trim(),
          memoriKey: userMemoriKey.trim(),
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save profile");
      }
      setProfile(updatedProfile);
      setHasProfile(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    }
  };

  return (
    <div className="dashboard">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="sidebar-header">
          <img src={memoriLogo} alt="Memori" className="sidebar-logo" />
          {!sidebarCollapsed && <span className="sidebar-title">Wellness Coach</span>}
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
            {!sidebarCollapsed && <span>Profile</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "daily" ? "active" : ""}`}
            onClick={() => setActiveTab("daily")}
            disabled={!hasProfile || !userId.trim()}
          >
            <span className="nav-icon">📝</span>
            {!sidebarCollapsed && <span>Daily Log</span>}
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
            className={`nav-item ${activeTab === "plan" ? "active" : ""}`}
            onClick={() => setActiveTab("plan")}
            disabled={!hasProfile || !userId.trim()}
          >
            <span className="nav-icon">🎯</span>
            {!sidebarCollapsed && <span>Wellness Plan</span>}
          </button>
          <button
            className={`nav-item ${activeTab === "checkin" ? "active" : ""}`}
            onClick={() => setActiveTab("checkin")}
            disabled={!hasProfile || !userId.trim()}
          >
            <span className="nav-icon">📅</span>
            {!sidebarCollapsed && <span>Weekly Check-In</span>}
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
          <div className="notification warning" onClick={() => setShowKeysModal(true)} style={{ cursor: 'pointer' }}>
            <span className="notification-icon">🔑</span>
            Please set your OpenAI and Memori API keys to use the app. Click here or the button above to configure.
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
        <div className="tab-content">
          {activeTab === "profile" && (
            <ProfileTab
              profile={profile}
              onSave={handleSaveProfile}
              apiBase={API_BASE}
              userId={userId}
              openaiKey={userOpenaiKey}
              memoriKey={userMemoriKey}
            />
          )}
          {activeTab === "daily" && (
            <DailyLogTab
              apiBase={API_BASE}
              userId={userId}
              openaiKey={userOpenaiKey}
              memoriKey={userMemoriKey}
            />
          )}
          {activeTab === "analytics" && (
            <AnalyticsTab
              apiBase={API_BASE}
              userId={userId}
            />
          )}
          {activeTab === "plan" && (
            <WellnessPlanTab
              profile={profile}
              apiBase={API_BASE}
              userId={userId}
              openaiKey={userOpenaiKey}
              memoriKey={userMemoriKey}
            />
          )}
          {activeTab === "checkin" && (
            <CheckInTab
              profile={profile}
              apiBase={API_BASE}
              userId={userId}
              openaiKey={userOpenaiKey}
              memoriKey={userMemoriKey}
            />
          )}
        </div>
      </main>

      {/* API Keys Modal */}
      {showKeysModal && (
        <div className="modal-overlay" onClick={() => setShowKeysModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>API Keys Configuration</h2>
              <button className="modal-close" onClick={() => setShowKeysModal(false)}>
                ×
              </button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: "16px", color: "var(--color-text-secondary)" }}>
                Enter your OpenAI and Memori API keys. These are stored locally in your browser.
              </p>
              <div className="form-group">
                <label htmlFor="openai-key">OpenAI API Key</label>
                <input
                  id="openai-key"
                  type="password"
                  value={userOpenaiKey}
                  onChange={(e) => setUserOpenaiKey(e.target.value)}
                  placeholder="sk-..."
                  className="form-input"
                />
              </div>
              <div className="form-group">
                <label htmlFor="memori-key">Memori API Key</label>
                <input
                  id="memori-key"
                  type="password"
                  value={userMemoriKey}
                  onChange={(e) => setUserMemoriKey(e.target.value)}
                  placeholder="Enter your Memori key..."
                  className="form-input"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowKeysModal(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleSaveApiKeys}>
                Save Keys
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
