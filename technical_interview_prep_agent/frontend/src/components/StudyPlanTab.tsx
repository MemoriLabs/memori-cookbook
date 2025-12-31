import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { CandidateProfile } from "../types";

type DueProblem = {
  id: number;
  title: string;
  difficulty: string;
  patterns: string[];
  nextReviewAt: string;
};

type StudyPlan = {
  planId: number;
  weekNumber: number;
  focusPatterns: string[];
  planMarkdown: string;
};

type Props = {
  apiBase: string;
  userId: string;
  profile: CandidateProfile;
  openaiKey?: string;
  memoriKey?: string;
};

function StudyPlanTab({ apiBase, userId, profile, openaiKey, memoriKey }: Props) {
  const [dueProblems, setDueProblems] = useState<DueProblem[]>([]);
  const [studyPlan, setStudyPlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Company presets
  const companies = ["Google", "Meta", "Amazon", "Apple", "Microsoft", "Netflix", "Stripe"];
  const [selectedCompany, setSelectedCompany] = useState<string>("");

  useEffect(() => {
    if (!userId) return;
    loadDueProblems();
    loadStudyPlan();
  }, [userId]);

  const loadDueProblems = async () => {
    try {
      const res = await fetch(`${apiBase}/review/due/${encodeURIComponent(userId)}?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setDueProblems(data.problems || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadStudyPlan = async () => {
    try {
      const res = await fetch(`${apiBase}/study-plan/${encodeURIComponent(userId)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.plans && data.plans.length > 0) {
          setStudyPlan({
            planId: data.plans[0].id,
            weekNumber: data.plans[0].weekNumber,
            focusPatterns: data.plans[0].focusPatterns,
            planMarkdown: data.plans[0].planMarkdown,
          });
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const generateStudyPlan = async () => {
    setGenerating(true);
    try {
      const res = await fetch(`${apiBase}/study-plan/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          openaiKey,
          memoriKey,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setStudyPlan({
          planId: data.planId,
          weekNumber: data.weekNumber,
          focusPatterns: data.focusPatterns,
          planMarkdown: data.planMarkdown,
        });
      }
    } catch (e) {
      console.error(e);
      alert("Failed to generate study plan");
    } finally {
      setGenerating(false);
    }
  };

  const markReviewComplete = async (attemptId: number, wasCorrect: boolean) => {
    try {
      await fetch(`${apiBase}/review/complete/${attemptId}?was_correct=${wasCorrect}`, {
        method: "POST",
      });
      loadDueProblems();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📅 Study Plan & Review</h2>

      {/* Spaced Repetition Review */}
      <div className="card">
        <h3>🔄 Due for Review (Spaced Repetition)</h3>
        <p className="subtle">
          Problems you've attempted before that are due for review. Reviewing helps reinforce learning!
        </p>

        {dueProblems.length > 0 ? (
          <div className="due-list">
            {dueProblems.map((problem) => (
              <div key={problem.id} className="due-item">
                <div className="due-info">
                  <span className="due-title">{problem.title}</span>
                  <div className="due-meta">
                    <span className={`badge-small ${problem.difficulty.toLowerCase()}`}>
                      {problem.difficulty}
                    </span>
                    {problem.patterns.slice(0, 2).map((p) => (
                      <span key={p} className="badge-small">{p}</span>
                    ))}
                  </div>
                </div>
                <div className="due-actions">
                  <button
                    className="btn-small success"
                    onClick={() => markReviewComplete(problem.id, true)}
                    title="I remember this!"
                  >
                    ✓ Got it
                  </button>
                  <button
                    className="btn-small"
                    onClick={() => markReviewComplete(problem.id, false)}
                    title="Need more practice"
                  >
                    ✗ Review again
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-state">No problems due for review. Keep practicing!</p>
        )}
      </div>

      {/* Company-Specific Prep */}
      <div className="card">
        <h3>🏢 Company-Specific Prep</h3>
        <p className="subtle">
          Focus on problem patterns commonly asked at specific companies.
        </p>
        <div className="company-grid">
          {companies.map((company) => (
            <button
              key={company}
              className={`company-chip ${selectedCompany === company ? "selected" : ""}`}
              onClick={() => setSelectedCompany(company)}
            >
              {company}
            </button>
          ))}
        </div>
        {selectedCompany && (
          <div className="company-info">
            <p>
              <strong>{selectedCompany}</strong> interviews typically focus on:
            </p>
            <ul>
              {selectedCompany === "Google" && (
                <>
                  <li>Graphs & Graph Algorithms (BFS, DFS, Dijkstra)</li>
                  <li>Dynamic Programming</li>
                  <li>System Design at scale</li>
                </>
              )}
              {selectedCompany === "Meta" && (
                <>
                  <li>Trees & Graph traversals</li>
                  <li>String manipulation</li>
                  <li>Product-focused system design</li>
                </>
              )}
              {selectedCompany === "Amazon" && (
                <>
                  <li>Leadership Principles (behavioral)</li>
                  <li>Trees and Arrays</li>
                  <li>Object-Oriented Design</li>
                </>
              )}
              {selectedCompany === "Apple" && (
                <>
                  <li>Arrays and Strings</li>
                  <li>Linked Lists</li>
                  <li>Clean code and attention to detail</li>
                </>
              )}
              {selectedCompany === "Microsoft" && (
                <>
                  <li>Trees and Graphs</li>
                  <li>Dynamic Programming</li>
                  <li>System Design</li>
                </>
              )}
              {selectedCompany === "Netflix" && (
                <>
                  <li>System Design & Distributed Systems</li>
                  <li>Caching strategies</li>
                  <li>Streaming architecture</li>
                </>
              )}
              {selectedCompany === "Stripe" && (
                <>
                  <li>API Design</li>
                  <li>String parsing and validation</li>
                  <li>Payment system design</li>
                </>
              )}
            </ul>
          </div>
        )}
      </div>

      {/* AI Study Plan */}
      <div className="card">
        <h3>🤖 AI-Generated Study Plan</h3>
        <p className="subtle">
          Get a personalized weekly study plan based on your weak patterns and goals.
        </p>

        {studyPlan ? (
          <div className="study-plan-content">
            <div className="plan-header">
              <span className="plan-week">Week {studyPlan.weekNumber}</span>
              <div className="plan-patterns">
                Focus: {studyPlan.focusPatterns.slice(0, 3).join(", ")}
              </div>
            </div>
            <ReactMarkdown className="markdown">{studyPlan.planMarkdown}</ReactMarkdown>
            <button onClick={generateStudyPlan} disabled={generating}>
              {generating ? "Generating..." : "🔄 Generate New Plan"}
            </button>
          </div>
        ) : (
          <div className="plan-empty">
            <p>No study plan yet. Generate one based on your profile and progress!</p>
            <button className="primary" onClick={generateStudyPlan} disabled={generating}>
              {generating ? "Generating..." : "✨ Generate Study Plan"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default StudyPlanTab;
