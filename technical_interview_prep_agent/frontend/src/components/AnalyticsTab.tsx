import React, { useEffect, useState } from "react";

type PatternStat = {
  total: number;
  correct: number;
  incorrect: number;
  partial: number;
};

type DifficultyStat = {
  total: number;
  correct: number;
};

type WeeklyData = {
  week: string;
  count: number;
};

type Analytics = {
  totalAttempts: number;
  correctAttempts: number;
  accuracy: number;
  patternStats: Record<string, PatternStat>;
  difficultyStats: Record<string, DifficultyStat>;
  weeklyActivity: WeeklyData[];
};

type Props = {
  apiBase: string;
  userId: string;
};

function AnalyticsTab({ apiBase, userId }: Props) {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [resumeBullets, setResumeBullets] = useState<string[]>([]);

  useEffect(() => {
    if (!userId) return;

    const loadAnalytics = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${apiBase}/analytics/${encodeURIComponent(userId)}`);
        if (res.ok) {
          const data = await res.json();
          setAnalytics(data);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };

    loadAnalytics();
  }, [userId, apiBase]);

  const handleExportMarkdown = async () => {
    setExportLoading(true);
    try {
      const res = await fetch(`${apiBase}/export/${encodeURIComponent(userId)}/markdown`);
      if (res.ok) {
        const text = await res.text();
        const blob = new Blob([text], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `interview-prep-${userId}.md`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setExportLoading(false);
    }
  };

  const handleGetResumeBullets = async () => {
    try {
      const res = await fetch(`${apiBase}/export/${encodeURIComponent(userId)}/resume-bullets`);
      if (res.ok) {
        const data = await res.json();
        setResumeBullets(data.bullets || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="tab-panel">
        <h2>📊 Analytics</h2>
        <div className="banner info">Loading analytics...</div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="tab-panel">
        <h2>📊 Analytics</h2>
        <div className="empty-state">
          Complete some practice problems to see your analytics!
        </div>
      </div>
    );
  }

  const sortedPatterns = Object.entries(analytics.patternStats)
    .sort((a, b) => b[1].total - a[1].total);

  const maxCount = Math.max(...analytics.weeklyActivity.map(w => w.count), 1);

  return (
    <div className="tab-panel">
      <h2>📊 Analytics Dashboard</h2>

      {/* Overview Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value-large">{analytics.totalAttempts}</div>
          <div className="stat-label">Total Problems</div>
        </div>
        <div className="stat-card">
          <div className="stat-value-large">{analytics.correctAttempts}</div>
          <div className="stat-label">Correct</div>
        </div>
        <div className="stat-card">
          <div className="stat-value-large accent">{analytics.accuracy}%</div>
          <div className="stat-label">Accuracy</div>
        </div>
      </div>

      {/* Difficulty Breakdown */}
      <div className="card">
        <h3>By Difficulty</h3>
        <div className="difficulty-bars">
          {["Easy", "Medium", "Hard"].map((diff) => {
            const stats = analytics.difficultyStats[diff] || { total: 0, correct: 0 };
            const pct = stats.total > 0 ? Math.round(stats.correct / stats.total * 100) : 0;
            return (
              <div key={diff} className="difficulty-row">
                <span className={`diff-label ${diff.toLowerCase()}`}>{diff}</span>
                <div className="progress-bar-container">
                  <div
                    className={`progress-bar ${diff.toLowerCase()}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="diff-stats">{stats.correct}/{stats.total} ({pct}%)</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Pattern Breakdown */}
      <div className="card">
        <h3>By Pattern</h3>
        <div className="pattern-grid">
          {sortedPatterns.slice(0, 12).map(([pattern, stats]) => {
            const accuracy = stats.total > 0 ? Math.round(stats.correct / stats.total * 100) : 0;
            return (
              <div key={pattern} className="pattern-item">
                <div className="pattern-header">
                  <span className="pattern-name">{pattern}</span>
                  <span className="pattern-accuracy">{accuracy}%</span>
                </div>
                <div className="mini-progress">
                  <div
                    className="mini-progress-fill"
                    style={{
                      width: `${accuracy}%`,
                      backgroundColor: accuracy >= 70 ? 'var(--color-success)' :
                                       accuracy >= 40 ? 'var(--color-warning)' : 'var(--color-error)'
                    }}
                  />
                </div>
                <div className="pattern-count">{stats.total} problems</div>
              </div>
            );
          })}
        </div>
        {sortedPatterns.length === 0 && (
          <p className="subtle">No pattern data yet. Complete more problems!</p>
        )}
      </div>

      {/* Weekly Activity */}
      <div className="card">
        <h3>Weekly Activity</h3>
        <div className="activity-chart">
          {analytics.weeklyActivity.slice(-12).map((week) => (
            <div key={week.week} className="activity-bar-wrapper">
              <div
                className="activity-bar"
                style={{ height: `${(week.count / maxCount) * 100}%` }}
                title={`${week.week}: ${week.count} problems`}
              />
              <span className="activity-label">
                {new Date(week.week).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Export Section */}
      <div className="card">
        <h3>Export & Share</h3>
        <div className="export-actions">
          <button onClick={handleExportMarkdown} disabled={exportLoading}>
            {exportLoading ? "Exporting..." : "📄 Export as Markdown"}
          </button>
          <button onClick={handleGetResumeBullets}>
            📝 Generate Resume Bullets
          </button>
        </div>

        {resumeBullets.length > 0 && (
          <div className="resume-bullets">
            <h4>Resume Bullet Points</h4>
            <ul>
              {resumeBullets.map((bullet, i) => (
                <li key={i}>{bullet}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export default AnalyticsTab;
