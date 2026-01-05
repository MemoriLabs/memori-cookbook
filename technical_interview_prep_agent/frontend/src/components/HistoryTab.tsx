import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

type Attempt = {
  id: number;
  title: string;
  difficulty: string;
  patterns: string[];
  verdict: string;
  createdAt: string;
  language: string;
  hintsUsed: number;
  code: string;
  evaluationMarkdown: string;
  nextReviewAt: string | null;
};

type Props = {
  apiBase: string;
  userId: string;
};

function HistoryTab({ apiBase, userId }: Props) {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedAttempt, setSelectedAttempt] = useState<Attempt | null>(null);

  // Filters
  const [difficulty, setDifficulty] = useState<string>("");
  const [verdict, setVerdict] = useState<string>("");
  const [pattern, setPattern] = useState<string>("");

  const loadHistory = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/attempts/history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          difficulty: difficulty || null,
          verdict: verdict || null,
          pattern: pattern || null,
          limit: 50,
          offset: 0,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setAttempts(data.attempts || []);
        setTotal(data.total || 0);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [userId, difficulty, verdict, pattern]);

  const getVerdictClass = (v: string) => {
    if (v === "correct") return "verdict-correct";
    if (v === "incorrect") return "verdict-incorrect";
    return "verdict-partial";
  };

  const handleBookmark = async (attemptId: number) => {
    try {
      await fetch(`${apiBase}/bookmarks/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          attemptId,
          collectionName: "Saved",
        }),
      });
      alert("Bookmarked!");
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📚 Problem History</h2>
      <p className="subtle">View and retry your past problems. Filter by difficulty, pattern, or verdict.</p>

      {/* Filters */}
      <div className="filters-row">
        <div className="filter-group">
          <label>Difficulty</label>
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="">All</option>
            <option value="Easy">Easy</option>
            <option value="Medium">Medium</option>
            <option value="Hard">Hard</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Verdict</label>
          <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
            <option value="">All</option>
            <option value="correct">Correct</option>
            <option value="partially_correct">Partial</option>
            <option value="incorrect">Incorrect</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Pattern</label>
          <input
            type="text"
            value={pattern}
            placeholder="e.g. arrays, trees"
            onChange={(e) => setPattern(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="banner info">Loading history...</div>
      ) : (
        <>
          <p className="subtle">Showing {attempts.length} of {total} attempts</p>

          <div className="history-list">
            {attempts.map((attempt) => (
              <div key={attempt.id} className="history-item">
                <div className="history-main">
                  <div className="history-header">
                    <span className="history-title">{attempt.title}</span>
                    <span className={`badge-small ${attempt.difficulty.toLowerCase()}`}>
                      {attempt.difficulty}
                    </span>
                    <span className={`badge-small ${getVerdictClass(attempt.verdict)}`}>
                      {attempt.verdict.replace("_", " ")}
                    </span>
                  </div>
                  <div className="history-meta">
                    <span>{new Date(attempt.createdAt).toLocaleDateString()}</span>
                    <span>•</span>
                    <span>{attempt.language}</span>
                    <span>•</span>
                    <span>{attempt.hintsUsed} hints used</span>
                    {attempt.patterns.length > 0 && (
                      <>
                        <span>•</span>
                        <span>{attempt.patterns.slice(0, 3).join(", ")}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="history-actions">
                  <button className="btn-small" onClick={() => setSelectedAttempt(attempt)}>
                    View
                  </button>
                  <button className="btn-small" onClick={() => handleBookmark(attempt.id)}>
                    ⭐
                  </button>
                </div>
              </div>
            ))}

            {attempts.length === 0 && (
              <div className="empty-state">
                No attempts found. Start practicing to build your history!
              </div>
            )}
          </div>
        </>
      )}

      {/* Detail Modal */}
      {selectedAttempt && (
        <div className="modal-overlay" onClick={() => setSelectedAttempt(null)}>
          <div className="modal modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedAttempt.title}</h2>
              <button className="modal-close" onClick={() => setSelectedAttempt(null)}>×</button>
            </div>
            <div className="modal-body">
              <div className="detail-badges">
                <span className={`badge-small ${selectedAttempt.difficulty.toLowerCase()}`}>
                  {selectedAttempt.difficulty}
                </span>
                <span className={`badge-small ${getVerdictClass(selectedAttempt.verdict)}`}>
                  {selectedAttempt.verdict.replace("_", " ")}
                </span>
                <span className="badge-small">{selectedAttempt.language}</span>
              </div>

              <h3>Your Code</h3>
              <pre className="code-block">{selectedAttempt.code}</pre>

              <h3>Evaluation</h3>
              <ReactMarkdown className="markdown">
                {selectedAttempt.evaluationMarkdown}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default HistoryTab;
