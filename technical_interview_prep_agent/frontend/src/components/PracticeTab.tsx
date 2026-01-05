import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { CandidateProfile, ProblemMetadata } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  profile: CandidateProfile;
  problem: ProblemMetadata | null;
  setProblem: (p: ProblemMetadata | null) => void;
  solutionCode: string;
  setSolutionCode: (code: string) => void;
  hints: string[];
  setHints: (hints: string[]) => void;
  evaluationMarkdown: string;
  setEvaluationMarkdown: (md: string) => void;
  openaiKey?: string;
  memoriKey?: string;
};

const difficultyOptions = ["Easy", "Medium", "Hard"];

const patternOptions = [
  "arrays",
  "strings",
  "hashing",
  "two-pointers",
  "sliding window",
  "linked list",
  "binary tree",
  "binary search tree",
  "graphs",
  "DFS",
  "BFS",
  "dynamic programming",
  "greedy",
  "backtracking",
  "heap/priority queue",
  "sorting"
];

const languageOptions = [
  "Python",
  "Java",
  "C++",
  "JavaScript/TypeScript",
  "Go",
  "Other"
];

function PracticeTab({
  apiBase,
  userId,
  profile,
  problem,
  setProblem,
  solutionCode,
  setSolutionCode,
  hints,
  setHints,
  evaluationMarkdown,
  setEvaluationMarkdown,
  openaiKey,
  memoriKey
}: Props) {
  const [difficulty, setDifficulty] = useState<string>("Medium");
  const [selectedPatterns, setSelectedPatterns] = useState<string[]>([]);
  const [language, setLanguage] = useState<string>(profile.primary_language || "Python");
  const [loadingProblem, setLoadingProblem] = useState(false);
  const [loadingHint, setLoadingHint] = useState(false);
  const [loadingEval, setLoadingEval] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const togglePattern = (pattern: string) => {
    if (selectedPatterns.includes(pattern)) {
      setSelectedPatterns(selectedPatterns.filter((p) => p !== pattern));
    } else {
      setSelectedPatterns([...selectedPatterns, pattern]);
    }
  };

  const handleGenerateProblem = async () => {
    if (!userId) return;
    setError(null);
    setLoadingProblem(true);
    try {
      const res = await fetch(`${apiBase}/problem`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          difficulty,
          patterns: selectedPatterns,
          openaiKey,
          memoriKey
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to generate problem");
      }
      const data = await res.json();
      setProblem(data);
      setSolutionCode("");
      setHints([]);
      setEvaluationMarkdown("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoadingProblem(false);
    }
  };

  const handleHint = async () => {
    if (!userId || !problem) return;
    setError(null);
    setLoadingHint(true);
    try {
      const res = await fetch(`${apiBase}/hint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          problem,
          language,
          codeSoFar: solutionCode,
          hintIndex: hints.length + 1,
          openaiKey,
          memoriKey
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to generate hint");
      }
      const data = await res.json();
      setHints([...hints, data.hint]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoadingHint(false);
    }
  };

  const handleEvaluate = async () => {
    if (!userId || !problem) return;
    if (!solutionCode.trim()) {
      setError("Please write some code before requesting a review.");
      return;
    }
    setError(null);
    setLoadingEval(true);
    try {
      const res = await fetch(`${apiBase}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          problem,
          language,
          candidateCode: solutionCode,
          hints,
          openaiKey,
          memoriKey
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to evaluate solution");
      }
      const data = await res.json();
      setEvaluationMarkdown(data.evaluationMarkdown ?? "");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setLoadingEval(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>🧠 Practice Session (Problems, Hints, Evaluation)</h2>

      {!profile.name && (
        <div className="banner info">
          Set up your candidate profile first in the <strong>Profile &amp; Goals</strong> tab.
        </div>
      )}

      <section className="card">
        <h3>1. Configure a problem</h3>
        <div className="two-column">
          <div className="column">
            <label>
              Desired difficulty
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                {difficultyOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="column">
            <label>Focus patterns</label>
            <div className="chips">
              {patternOptions.map((p) => (
                <button
                  key={p}
                  type="button"
                  className={
                    selectedPatterns.includes(p) ? "chip chip-selected" : "chip"
                  }
                  onClick={() => togglePattern(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
        <button
          type="button"
          className="primary"
          onClick={handleGenerateProblem}
          disabled={loadingProblem || !profile.name}
        >
          {loadingProblem ? "Generating problem…" : "Generate personalized problem"}
        </button>
      </section>

      {problem ? (
        <>
          <section className="card">
            <h3>2. Current problem</h3>
            <p>
              <strong>Title:</strong> {problem.title}
            </p>
            <p>
              <strong>Difficulty:</strong> {problem.difficulty}
            </p>
            {problem.patterns?.length > 0 && (
              <p>
                <strong>Patterns:</strong> {problem.patterns.join(", ")}
              </p>
            )}
            <hr />
            <ReactMarkdown className="markdown">{problem.statement}</ReactMarkdown>
          </section>

          <section className="card">
            <h3>3. Write your solution</h3>
            <label>
              Language
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                {[profile.primary_language, ...languageOptions]
                  .filter((v, i, arr) => arr.indexOf(v) === i)
                  .map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Solution code
              <textarea
                rows={12}
                value={solutionCode}
                placeholder={`Write your ${language} solution here…`}
                onChange={(e) => setSolutionCode(e.target.value)}
              />
            </label>

            <div className="button-row">
              <button
                type="button"
                onClick={handleHint}
                disabled={loadingHint}
              >
                {loadingHint ? "Requesting hint…" : "Request hint"}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={handleEvaluate}
                disabled={loadingEval}
              >
                {loadingEval ? "Submitting for review…" : "Submit solution for review"}
              </button>
            </div>
          </section>

          {hints.length > 0 && (
            <section className="card">
              <h3>💡 Hints so far</h3>
              {hints.map((hint, i) => (
                <details
                  key={i}
                  open={i === hints.length - 1}
                  className="hint-expander"
                >
                  <summary>Hint {i + 1}</summary>
                  <ReactMarkdown className="markdown">{hint}</ReactMarkdown>
                </details>
              ))}
            </section>
          )}

          {evaluationMarkdown && (
            <section className="card">
              <h3>🎯 Coach feedback</h3>
              <ReactMarkdown className="markdown">
                {evaluationMarkdown}
              </ReactMarkdown>
            </section>
          )}
        </>
      ) : (
        <section className="card muted">
          <p>Generate a problem above to start a practice session.</p>
        </section>
      )}

      {error && <div className="banner error">{error}</div>}
    </div>
  );
}

export default PracticeTab;
