import React, { useState, useEffect } from "react";
import { FinancialProfile, FinancialGoal } from "../types";
import ReactMarkdown from "react-markdown";

type Props = {
  apiBase: string;
  userId: string;
  profile: FinancialProfile;
  openaiKey?: string;
  memoriKey?: string;
};

function GoalsTab({ apiBase, userId, profile, openaiKey, memoriKey }: Props) {
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const [newGoal, setNewGoal] = useState<FinancialGoal>({
    name: "",
    target_amount: 0,
    current_amount: 0,
    priority: "Medium",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [goalPlan, setGoalPlan] = useState<string | null>(null);

  useEffect(() => {
    if (userId) {
      loadGoals();
    }
  }, [userId]);

  const loadGoals = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/goals/${userId}`);
      if (res.ok) {
        const data = await res.json();
        setGoals(data.goals || []);
      }
    } catch (e) {
      // Ignore errors
    } finally {
      setLoading(false);
    }
  };

  const handleCreateGoal = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!userId) {
      setError("Please enter a User ID at the top.");
      return;
    }

    if (!newGoal.name || !newGoal.target_amount || newGoal.target_amount <= 0) {
      setError("Please enter a goal name and target amount.");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/goals/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          goal: newGoal,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to create goal");
      }
      setSuccess("Goal created!");
      setNewGoal({
        name: "",
        target_amount: 0,
        current_amount: 0,
        priority: "Medium",
      });
      await loadGoals();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateGoal = async (goalId: number, currentAmount: number) => {
    try {
      const res = await fetch(`${apiBase}/goals/${userId}/${goalId}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_amount: currentAmount }),
      });
      if (res.ok) {
        await loadGoals();
      }
    } catch (e) {
      // Ignore errors
    }
  };

  const handleGeneratePlan = async () => {
    if (!userId || !profile.name) {
      setError("Please set up your profile first.");
      return;
    }

    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/goals/generate`, {
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
        throw new Error(data.detail ?? "Failed to generate goal plan");
      }
      const data = await res.json();
      setGoalPlan(data.goalMarkdown || "");
      setSuccess("Goal plan generated!");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>🎯 Financial Goals</h2>

      <section>
        <h3>Create New Goal</h3>
        <form className="profile-form" onSubmit={handleCreateGoal}>
          <div className="two-column">
            <div className="column">
              <label>
                Goal Name
                <input
                  type="text"
                  value={newGoal.name}
                  placeholder="e.g. Emergency Fund"
                  onChange={(e) => setNewGoal({ ...newGoal, name: e.target.value })}
                  required
                />
              </label>
              <label>
                Target Amount
                <input
                  type="number"
                  step="0.01"
                  value={newGoal.target_amount || ""}
                  placeholder="0.00"
                  onChange={(e) => setNewGoal({ ...newGoal, target_amount: e.target.value ? parseFloat(e.target.value) : 0 })}
                  required
                />
              </label>
            </div>
            <div className="column">
              <label>
                Current Amount
                <input
                  type="number"
                  step="0.01"
                  value={newGoal.current_amount || ""}
                  placeholder="0.00"
                  onChange={(e) => setNewGoal({ ...newGoal, current_amount: e.target.value ? parseFloat(e.target.value) : 0 })}
                />
              </label>
              <label>
                Priority
                <select
                  value={newGoal.priority}
                  onChange={(e) => setNewGoal({ ...newGoal, priority: e.target.value })}
                >
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </label>
              <label>
                Target Date (optional)
                <input
                  type="date"
                  value={newGoal.target_date || ""}
                  onChange={(e) => setNewGoal({ ...newGoal, target_date: e.target.value || undefined })}
                />
              </label>
            </div>
          </div>
          <label>
            Description (optional)
            <textarea
              value={newGoal.description || ""}
              placeholder="Additional details..."
              onChange={(e) => setNewGoal({ ...newGoal, description: e.target.value || undefined })}
              rows={3}
            />
          </label>
          <div className="form-actions">
            <button type="submit" className="primary" disabled={saving || !userId}>
              {saving ? "Creating…" : "Create Goal"}
            </button>
          </div>
        </form>
      </section>

      {error && <div className="banner error">{error}</div>}
      {success && <div className="banner success">{success}</div>}

      <section style={{ marginTop: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h3>Your Goals</h3>
          <button
            className="btn-primary"
            onClick={handleGeneratePlan}
            disabled={generating || !userId || !profile.name}
          >
            {generating ? "Generating…" : "Generate Goal Plan"}
          </button>
        </div>
        {loading ? (
          <p>Loading...</p>
        ) : goals.length === 0 ? (
          <p>No goals set yet. Create a goal above!</p>
        ) : (
          <div className="goals-list">
            {goals.map((goal) => {
              const progress = goal.target_amount > 0
                ? (goal.current_amount / goal.target_amount) * 100
                : 0;
              return (
                <div key={goal.id} className="goal-item">
                  <div className="goal-header">
                    <span className="goal-name">{goal.name}</span>
                    <span className="goal-priority">{goal.priority}</span>
                  </div>
                  <div className="goal-progress">
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${Math.min(progress, 100)}%`,
                          backgroundColor: "var(--color-accent-primary)",
                        }}
                      />
                    </div>
                    <div className="goal-amounts">
                      <span>${goal.current_amount.toFixed(2)} / ${goal.target_amount.toFixed(2)}</span>
                      <span>{progress.toFixed(1)}%</span>
                    </div>
                  </div>
                  <div className="goal-actions">
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Update amount"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && goal.id) {
                          handleUpdateGoal(goal.id, parseFloat((e.target as HTMLInputElement).value) || 0);
                          (e.target as HTMLInputElement).value = "";
                        }
                      }}
                      style={{ width: "200px", marginRight: "8px" }}
                    />
                    {goal.target_date && (
                      <span className="goal-date">
                        Target: {new Date(goal.target_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {goalPlan && (
        <section style={{ marginTop: "2rem" }}>
          <h3>AI-Generated Goal Plan</h3>
          <div className="markdown-content">
            <ReactMarkdown>{goalPlan}</ReactMarkdown>
          </div>
        </section>
      )}
    </div>
  );
}

export default GoalsTab;
