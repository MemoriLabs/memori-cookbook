import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { CandidateProfile, ProblemMetadata } from "../types";

type MockSession = {
  sessionId: string;
  timeLimitMinutes: number;
  numProblems: number;
  difficulties: string[];
};

type Props = {
  apiBase: string;
  userId: string;
  profile: CandidateProfile;
  openaiKey?: string;
  memoriKey?: string;
};

function MockInterviewTab({ apiBase, userId, profile, openaiKey, memoriKey }: Props) {
  const [session, setSession] = useState<MockSession | null>(null);
  const [currentProblemIndex, setCurrentProblemIndex] = useState(0);
  const [problems, setProblems] = useState<ProblemMetadata[]>([]);
  const [codes, setCodes] = useState<string[]>([]);
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [sessionResult, setSessionResult] = useState<{ score: number; problemsCompleted: number } | null>(null);
  const [pastSessions, setPastSessions] = useState<any[]>([]);

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Load past sessions
  useEffect(() => {
    if (!userId) return;

    const loadPastSessions = async () => {
      try {
        const res = await fetch(`${apiBase}/mock/history/${encodeURIComponent(userId)}`);
        if (res.ok) {
          const data = await res.json();
          setPastSessions(data.sessions || []);
        }
      } catch (e) {
        console.error(e);
      }
    };

    loadPastSessions();
  }, [userId, apiBase, sessionResult]);

  // Timer effect
  useEffect(() => {
    if (isRunning && timeRemaining > 0) {
      timerRef.current = setInterval(() => {
        setTimeRemaining((t) => {
          if (t <= 1) {
            setIsRunning(false);
            return 0;
          }
          return t - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRunning]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const startSession = async (sessionType: string) => {
    setLoading(true);
    try {
      // Start session
      const res = await fetch(`${apiBase}/mock/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          sessionType,
          timeLimitMinutes: sessionType === "phone_screen" ? 30 : 45,
          openaiKey,
          memoriKey,
        }),
      });

      if (!res.ok) throw new Error("Failed to start session");

      const sessionData = await res.json();
      setSession(sessionData);
      setTimeRemaining(sessionData.timeLimitMinutes * 60);
      setCurrentProblemIndex(0);
      setProblems([]);
      setCodes([]);
      setSessionResult(null);

      // Generate first problem
      await generateProblem(sessionData.difficulties[0], sessionData.sessionId);
      setIsRunning(true);
    } catch (e) {
      console.error(e);
      alert("Failed to start mock interview");
    } finally {
      setLoading(false);
    }
  };

  const generateProblem = async (difficulty: string, sessionId?: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/problem`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          difficulty,
          patterns: [],
          openaiKey,
          memoriKey,
        }),
      });

      if (!res.ok) throw new Error("Failed to generate problem");

      const problem = await res.json();
      setProblems((prev) => [...prev, problem]);
      setCodes((prev) => [...prev, ""]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const submitCurrentProblem = async () => {
    if (!session || !problems[currentProblemIndex]) return;

    setLoading(true);
    try {
      // Evaluate current problem
      await fetch(`${apiBase}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile,
          problem: problems[currentProblemIndex],
          language: profile.primary_language,
          candidateCode: codes[currentProblemIndex],
          hints: [],
          openaiKey,
          memoriKey,
        }),
      });

      // Move to next problem or complete
      if (currentProblemIndex < session.numProblems - 1) {
        setCurrentProblemIndex((i) => i + 1);
        await generateProblem(session.difficulties[currentProblemIndex + 1], session.sessionId);
      } else {
        await completeSession();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const completeSession = async () => {
    if (!session) return;

    setCompleting(true);
    setIsRunning(false);

    try {
      const res = await fetch(`${apiBase}/mock/complete/${session.sessionId}`, {
        method: "POST",
      });

      if (res.ok) {
        const result = await res.json();
        setSessionResult(result);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setCompleting(false);
    }
  };

  const endSession = () => {
    completeSession();
    setSession(null);
    setProblems([]);
    setCodes([]);
  };

  // Session complete screen
  if (sessionResult) {
    return (
      <div className="tab-panel">
        <h2>🎯 Mock Interview Complete!</h2>

        <div className="result-card">
          <div className="result-score">
            <span className="score-value">{Math.round(sessionResult.score)}</span>
            <span className="score-label">/ 100</span>
          </div>
          <p>You completed {sessionResult.problemsCompleted} problems</p>

          <div className="result-actions">
            <button className="primary" onClick={() => setSessionResult(null)}>
              Start New Session
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Active session
  if (session && problems.length > 0) {
    const currentProblem = problems[currentProblemIndex];

    return (
      <div className="tab-panel">
        <div className="mock-header">
          <h2>🎯 Mock Interview</h2>
          <div className="mock-status">
            <span className="problem-counter">
              Problem {currentProblemIndex + 1} / {session.numProblems}
            </span>
            <span className={`timer ${timeRemaining < 300 ? "timer-warning" : ""}`}>
              ⏱️ {formatTime(timeRemaining)}
            </span>
          </div>
        </div>

        {loading ? (
          <div className="banner info">Generating problem...</div>
        ) : (
          <>
            <div className="card">
              <div className="problem-header">
                <h3>{currentProblem.title}</h3>
                <span className={`badge-small ${currentProblem.difficulty.toLowerCase()}`}>
                  {currentProblem.difficulty}
                </span>
              </div>
              <ReactMarkdown className="markdown">{currentProblem.statement}</ReactMarkdown>
            </div>

            <div className="card">
              <label>
                Your Solution ({profile.primary_language})
                <textarea
                  rows={15}
                  value={codes[currentProblemIndex] || ""}
                  onChange={(e) => {
                    const newCodes = [...codes];
                    newCodes[currentProblemIndex] = e.target.value;
                    setCodes(newCodes);
                  }}
                  placeholder="Write your solution here..."
                  disabled={!isRunning}
                />
              </label>
            </div>

            <div className="mock-actions">
              <button
                className="primary"
                onClick={submitCurrentProblem}
                disabled={loading || !isRunning}
              >
                {currentProblemIndex < session.numProblems - 1
                  ? "Submit & Next Problem"
                  : "Submit & Finish"}
              </button>
              <button className="secondary" onClick={endSession}>
                End Session Early
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  // Session selection
  return (
    <div className="tab-panel">
      <h2>🎯 Mock Interview Mode</h2>
      <p className="subtle">
        Simulate real interview conditions with timed sessions. No hints allowed!
      </p>

      <div className="session-types">
        <div className="session-card" onClick={() => !loading && startSession("phone_screen")}>
          <div className="session-icon">📞</div>
          <h3>Phone Screen</h3>
          <p>30 minutes • 2 problems</p>
          <p className="session-details">Easy + Medium</p>
        </div>

        <div className="session-card" onClick={() => !loading && startSession("onsite")}>
          <div className="session-icon">🏢</div>
          <h3>Onsite</h3>
          <p>45 minutes • 3 problems</p>
          <p className="session-details">Medium + Medium + Hard</p>
        </div>
      </div>

      {loading && <div className="banner info">Starting session...</div>}

      {/* Past Sessions */}
      {pastSessions.length > 0 && (
        <div className="card">
          <h3>Recent Sessions</h3>
          <div className="past-sessions">
            {pastSessions.slice(0, 5).map((s) => (
              <div key={s.id} className="past-session-item">
                <span className="session-type-badge">{s.sessionType}</span>
                <span>{new Date(s.createdAt).toLocaleDateString()}</span>
                <span className="session-score">
                  {s.totalScore !== null ? `${Math.round(s.totalScore)}/100` : "In progress"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default MockInterviewTab;
