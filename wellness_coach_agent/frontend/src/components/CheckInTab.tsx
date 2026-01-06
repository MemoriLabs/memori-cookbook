import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { WellnessProfile } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  profile: WellnessProfile;
  openaiKey?: string;
  memoriKey?: string;
};

function CheckInTab({ apiBase, userId, profile, openaiKey, memoriKey }: Props) {
  const [loading, setLoading] = useState(false);
  const [conducting, setConducting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkIns, setCheckIns] = useState<any[]>([]);

  useEffect(() => {
    if (userId) {
      loadCheckInHistory();
    }
  }, [userId]);

  const loadCheckInHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/checkin/${userId}/history?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setCheckIns(data.checkIns || []);
      }
    } catch (e) {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  const conductCheckIn = async () => {
    setConducting(true);
    setError(null);
    try {
      const weekStart = new Date();
      weekStart.setDate(weekStart.getDate() - 7);

      const res = await fetch(`${apiBase}/checkin/weekly`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          weekStartDate: weekStart.toISOString(),
          openaiKey,
          memoriKey,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to conduct check-in");
      }
      await loadCheckInHistory();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setConducting(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📅 Weekly Check-In</h2>
      <p style={{ marginBottom: "24px", color: "var(--color-text-secondary)" }}>
        Conduct weekly assessments using LangGraph to review your progress, identify correlations, and get recommendations.
      </p>

      <div className="checkin-actions">
        <button
          className="btn-primary"
          onClick={conductCheckIn}
          disabled={conducting || !userId}
        >
          {conducting ? "Conducting Check-In..." : "Conduct Weekly Check-In"}
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}

      {loading ? (
        <p>Loading check-in history...</p>
      ) : checkIns.length > 0 ? (
        <section className="checkin-history">
          <h3>Check-In History</h3>
          {checkIns.map((checkIn) => (
            <div key={checkIn.id} className="checkin-card">
              <div className="checkin-header">
                <h4>
                  Week of {new Date(checkIn.weekStartDate).toLocaleDateString()}
                </h4>
                <span className="checkin-date">
                  {new Date(checkIn.createdAt).toLocaleDateString()}
                </span>
              </div>

              {checkIn.avgSleepHours && (
                <div className="checkin-metrics">
                  <span>Avg Sleep: {checkIn.avgSleepHours.toFixed(1)}h</span>
                  <span>Avg Mood: {checkIn.avgMoodScore?.toFixed(1) || "N/A"}</span>
                  <span>Exercise: {checkIn.totalExerciseMinutes || 0}min</span>
                  <span>Energy: {checkIn.avgEnergyLevel?.toFixed(1) || "N/A"}</span>
                </div>
              )}

              {checkIn.progressSummary && (
                <div className="checkin-section">
                  <h5>Progress Summary</h5>
                  <div className="progress-summary">
                    {Object.entries(checkIn.progressSummary).map(([key, value]: [string, any]) => (
                      <div key={key} className="progress-item">
                        <strong>{key}:</strong> {value}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {checkIn.correlationsFound && checkIn.correlationsFound.length > 0 && (
                <div className="checkin-section">
                  <h5>Correlations Found</h5>
                  <div className="correlations-list">
                    {checkIn.correlationsFound.map((corr: any, idx: number) => (
                      <div key={idx} className="correlation-item">
                        <span className="correlation-metrics">
                          {corr.metric1} ↔ {corr.metric2}
                        </span>
                        <span className={`correlation-badge ${corr.type}`}>
                          {corr.type === "positive" ? "↑" : "↓"} {Math.round(corr.strength * 100)}%
                        </span>
                        <p>{corr.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {checkIn.recommendations && checkIn.recommendations.length > 0 && (
                <div className="checkin-section">
                  <h5>Recommendations</h5>
                  <ul className="recommendations-list">
                    {checkIn.recommendations.map((rec: string, idx: number) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {checkIn.assessmentMarkdown && (
                <div className="checkin-section">
                  <h5>Full Assessment</h5>
                  <div className="markdown-content">
                    <ReactMarkdown>{checkIn.assessmentMarkdown}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          ))}
        </section>
      ) : (
        <div className="banner info">
          No check-ins yet. Conduct your first weekly check-in to get started!
        </div>
      )}
    </div>
  );
}

export default CheckInTab;
