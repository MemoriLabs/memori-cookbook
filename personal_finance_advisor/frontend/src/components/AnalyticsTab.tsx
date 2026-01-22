import React, { useState, useEffect } from "react";
import { FinancialProfile } from "../types";
import ReactMarkdown from "react-markdown";

type Props = {
  apiBase: string;
  userId: string;
  profile: FinancialProfile;
  openaiKey?: string;
  memoriKey?: string;
};

function AnalyticsTab({ apiBase, userId, profile, openaiKey, memoriKey }: Props) {
  const [analytics, setAnalytics] = useState<any>(null);
  const [assessment, setAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    if (userId) {
      loadAnalytics();
      loadLatestAssessment();
    }
  }, [userId]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/analytics/${userId}?days=30`);
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (e) {
      // Ignore errors
    } finally {
      setLoading(false);
    }
  };

  const loadLatestAssessment = async () => {
    try {
      const res = await fetch(`${apiBase}/assessment/${userId}/latest`);
      if (res.ok) {
        const data = await res.json();
        if (data.exists) {
          setAssessment(data.assessment);
        }
      }
    } catch (e) {
      // Ignore errors
    }
  };

  const handleGenerateAssessment = async () => {
    if (!userId || !profile.name) {
      setError("Please set up your profile first.");
      return;
    }

    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/assessment/health`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          openaiKey,
          memoriKey,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to generate assessment");
      }
      const data = await res.json();
      setAssessment({
        overallScore: data.overallScore,
        assessmentMarkdown: data.assessmentMarkdown,
        spendingAnalysis: data.spendingAnalysis,
        budgetAdherence: data.budgetAdherence,
        goalProgress: data.goalProgress,
        riskFactors: data.riskFactors,
        opportunities: data.opportunities,
        recommendations: data.recommendations,
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleAskQuestion = async () => {
    if (!question.trim() || !userId) {
      return;
    }

    setAsking(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/finance/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          question: question.trim(),
          openaiKey,
          memoriKey,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to get answer");
      }
      const data = await res.json();
      setAnswer(data.answer);
      setQuestion("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📈 Financial Analytics</h2>

      {error && <div className="banner error">{error}</div>}

      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h3>Financial Health Assessment</h3>
          <button
            className="btn-primary"
            onClick={handleGenerateAssessment}
            disabled={generating || !userId || !profile.name}
          >
            {generating ? "Generating…" : "Generate Assessment"}
          </button>
        </div>

        {assessment ? (
          <div className="assessment-content">
            <div className="assessment-score">
              <h4>Overall Financial Health Score</h4>
              <div className="score-circle" style={{
                background: `conic-gradient(var(--color-success) ${assessment.overallScore * 3.6}deg, var(--color-bg-tertiary) 0deg)`
              }}>
                <span className="score-value">{assessment.overallScore.toFixed(0)}</span>
              </div>
            </div>

            {assessment.assessmentMarkdown && (
              <div className="markdown-content">
                <ReactMarkdown>{assessment.assessmentMarkdown}</ReactMarkdown>
              </div>
            )}

            {assessment.recommendations && assessment.recommendations.length > 0 && (
              <div className="recommendations">
                <h4>Recommendations</h4>
                <ul>
                  {assessment.recommendations.map((rec: string, idx: number) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p>No assessment yet. Click "Generate Assessment" to get started.</p>
        )}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h3>Transaction Statistics (Last 30 Days)</h3>
        {loading ? (
          <p>Loading...</p>
        ) : analytics ? (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-label">Total Income</div>
              <div className="stat-value income">${analytics.stats?.totalIncome?.toFixed(2) || "0.00"}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total Expenses</div>
              <div className="stat-value expense">${analytics.stats?.totalExpenses?.toFixed(2) || "0.00"}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Net</div>
              <div className={`stat-value ${(analytics.stats?.net || 0) >= 0 ? "income" : "expense"}`}>
                ${analytics.stats?.net?.toFixed(2) || "0.00"}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Transactions</div>
              <div className="stat-value">{analytics.stats?.totalTransactions || 0}</div>
            </div>
          </div>
        ) : (
          <p>No transaction data yet.</p>
        )}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h3>Ask Your Financial Advisor</h3>
        <div className="question-form">
          <input
            type="text"
            value={question}
            placeholder="e.g. What are my biggest spending categories?"
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAskQuestion();
              }
            }}
            style={{ width: "100%", marginBottom: "8px" }}
          />
          <button
            className="btn-primary"
            onClick={handleAskQuestion}
            disabled={asking || !question.trim() || !userId}
          >
            {asking ? "Asking…" : "Ask"}
          </button>
        </div>
        {answer && (
          <div className="answer-content" style={{ marginTop: "1rem", padding: "1rem", background: "var(--color-bg-card)", borderRadius: "var(--radius-md)" }}>
            <p>{answer}</p>
          </div>
        )}
      </section>
    </div>
  );
}

export default AnalyticsTab;
