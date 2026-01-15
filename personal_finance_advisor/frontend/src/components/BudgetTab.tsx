import React, { useState, useEffect } from "react";
import { Budget } from "../types";

type Props = {
  apiBase: string;
  userId: string;
};

const categories = [
  "Food", "Transportation", "Entertainment", "Bills", "Shopping",
  "Healthcare", "Education", "Travel", "Subscriptions", "Other"
];

function BudgetTab({ apiBase, userId }: Props) {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [newBudget, setNewBudget] = useState<Budget>({
    category: "Food",
    monthly_limit: 0,
    currency: "USD",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [budgetStatus, setBudgetStatus] = useState<any[]>([]);

  useEffect(() => {
    if (userId) {
      loadBudgets();
      loadBudgetStatus();
    }
  }, [userId]);

  const loadBudgets = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/budgets/${userId}`);
      if (res.ok) {
        const data = await res.json();
        setBudgets(data.budgets || []);
      }
    } catch (e) {
      // Ignore errors
    } finally {
      setLoading(false);
    }
  };

  const loadBudgetStatus = async () => {
    try {
      const res = await fetch(`${apiBase}/budgets/${userId}/status`);
      if (res.ok) {
        const data = await res.json();
        setBudgetStatus(data.status || []);
      }
    } catch (e) {
      // Ignore errors
    }
  };

  const handleCreateBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!userId) {
      setError("Please enter a User ID at the top.");
      return;
    }

    if (!newBudget.monthly_limit || newBudget.monthly_limit <= 0) {
      setError("Please enter a valid monthly limit.");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/budgets/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          budget: newBudget,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to create budget");
      }
      setSuccess("Budget created!");
      setNewBudget({
        category: "Food",
        monthly_limit: 0,
        currency: "USD",
      });
      await loadBudgets();
      await loadBudgetStatus();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📊 Budget Management</h2>

      <section>
        <h3>Create New Budget</h3>
        <form className="profile-form" onSubmit={handleCreateBudget}>
          <div className="two-column">
            <div className="column">
              <label>
                Category
                <select
                  value={newBudget.category}
                  onChange={(e) => setNewBudget({ ...newBudget, category: e.target.value })}
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="column">
              <label>
                Monthly Limit
                <input
                  type="number"
                  step="0.01"
                  value={newBudget.monthly_limit || ""}
                  placeholder="0.00"
                  onChange={(e) => setNewBudget({ ...newBudget, monthly_limit: e.target.value ? parseFloat(e.target.value) : 0 })}
                  required
                />
              </label>
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="primary" disabled={saving || !userId}>
              {saving ? "Creating…" : "Create Budget"}
            </button>
          </div>
        </form>
      </section>

      {error && <div className="banner error">{error}</div>}
      {success && <div className="banner success">{success}</div>}

      <section style={{ marginTop: "2rem" }}>
        <h3>Budget Status</h3>
        {loading ? (
          <p>Loading...</p>
        ) : budgetStatus.length === 0 ? (
          <p>No budgets set yet. Create a budget above!</p>
        ) : (
          <div className="budget-list">
            {budgetStatus.map((status) => (
              <div key={status.budgetId} className={`budget-item ${status.isOverBudget ? "over-budget" : ""}`}>
                <div className="budget-header">
                  <span className="budget-category">{status.category}</span>
                  <span className="budget-limit">Limit: ${status.monthlyLimit.toFixed(2)}</span>
                </div>
                <div className="budget-progress">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${Math.min(status.percentage, 100)}%`,
                        backgroundColor: status.isOverBudget ? "var(--color-error)" : "var(--color-success)",
                      }}
                    />
                  </div>
                  <div className="budget-amounts">
                    <span>Spent: ${status.spent.toFixed(2)}</span>
                    <span>Remaining: ${status.remaining.toFixed(2)}</span>
                    <span>{status.percentage.toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default BudgetTab;
