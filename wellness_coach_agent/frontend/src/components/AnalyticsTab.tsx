import React, { useState, useEffect } from "react";

type Props = {
  apiBase: string;
  userId: string;
};

function AnalyticsTab({ apiBase, userId }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [weeklyActivity, setWeeklyActivity] = useState<any[]>([]);
  const [correlations, setCorrelations] = useState<any[]>([]);

  useEffect(() => {
    if (userId) {
      loadAnalytics();
      loadCorrelations();
    }
  }, [userId]);

  const loadAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/analytics/${userId}?days=30`);
      if (!res.ok) {
        throw new Error("Failed to load analytics");
      }
      const data = await res.json();
      setStats(data.stats);
      setWeeklyActivity(data.weeklyActivity || []);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const loadCorrelations = async () => {
    try {
      const res = await fetch(`${apiBase}/correlations/${userId}`);
      if (res.ok) {
        const data = await res.json();
        setCorrelations(data.correlations || []);
      }
    } catch (e) {
      // Ignore
    }
  };

  if (loading) {
    return (
      <div className="tab-panel">
        <h2>📊 Analytics</h2>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tab-panel">
        <h2>📊 Analytics</h2>
        <div className="banner error">{error}</div>
      </div>
    );
  }

  return (
    <div className="tab-panel">
      <h2>📊 Analytics & Insights</h2>
      <p style={{ marginBottom: "24px", color: "var(--color-text-secondary)" }}>
        View your wellness trends, statistics, and identified correlations.
      </p>

      {stats && (
        <section className="analytics-section">
          <h3>30-Day Summary</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.totalDays || 0}</div>
              <div className="stat-label">Days Logged</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.avgSleepHours?.toFixed(1) || "0"}</div>
              <div className="stat-label">Avg Sleep (hours)</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.avgMoodScore?.toFixed(1) || "0"}</div>
              <div className="stat-label">Avg Mood (1-10)</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.totalExerciseMinutes || 0}</div>
              <div className="stat-label">Total Exercise (min)</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.avgEnergyLevel?.toFixed(1) || "0"}</div>
              <div className="stat-label">Avg Energy (1-10)</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.avgStressLevel?.toFixed(1) || "0"}</div>
              <div className="stat-label">Avg Stress (1-10)</div>
            </div>
          </div>
        </section>
      )}

      {correlations.length > 0 && (
        <section className="analytics-section">
          <h3>Identified Correlations</h3>
          <div className="correlations-list">
            {correlations.map((corr, idx) => (
              <div key={idx} className="correlation-card">
                <div className="correlation-header">
                  <span className="correlation-metrics">
                    {corr.metric1} ↔ {corr.metric2}
                  </span>
                  <span className={`correlation-badge ${corr.correlationType}`}>
                    {corr.correlationType === "positive" ? "↑" : "↓"} {Math.round(corr.strength * 100)}%
                  </span>
                </div>
                <p className="correlation-description">{corr.description}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {weeklyActivity.length > 0 && (
        <section className="analytics-section">
          <h3>Weekly Trends</h3>
          <div className="weekly-trends">
            <table className="trends-table">
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Avg Sleep</th>
                  <th>Avg Mood</th>
                  <th>Exercise (min)</th>
                  <th>Avg Energy</th>
                </tr>
              </thead>
              <tbody>
                {weeklyActivity.slice(0, 12).map((week, idx) => (
                  <tr key={idx}>
                    <td>{new Date(week.week).toLocaleDateString()}</td>
                    <td>{week.avgSleepHours?.toFixed(1) || "-"}</td>
                    <td>{week.avgMoodScore?.toFixed(1) || "-"}</td>
                    <td>{week.totalExerciseMinutes || 0}</td>
                    <td>{week.avgEnergyLevel?.toFixed(1) || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!stats && !loading && (
        <div className="banner info">
          Start logging your daily habits to see analytics and correlations.
        </div>
      )}
    </div>
  );
}

export default AnalyticsTab;
