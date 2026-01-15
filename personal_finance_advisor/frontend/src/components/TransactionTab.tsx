import React, { useState, useEffect } from "react";
import { Transaction } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  openaiKey?: string;
  memoriKey?: string;
};

const categories = [
  "Food", "Transportation", "Entertainment", "Bills", "Shopping",
  "Healthcare", "Education", "Travel", "Subscriptions", "Other"
];

const paymentMethods = ["Credit Card", "Debit Card", "Cash", "Bank Transfer", "Other"];

function TransactionTab({ apiBase, userId, openaiKey, memoriKey }: Props) {
  const [today, setToday] = useState(new Date().toISOString().split("T")[0]);
  const [transaction, setTransaction] = useState<Transaction>({
    date: today,
    amount: 0,
    category: "Other",
    transaction_type: "expense",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (userId) {
      loadTransactions();
    }
  }, [userId]);

  const loadTransactions = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/transactions/get`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          limit: 50,
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
      }
    } catch (e) {
      // Ignore errors
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof Transaction, value: any) => {
    setTransaction({ ...transaction, [field]: value });
    setSuccess(null);
    setError(null);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!userId) {
      setError("Please enter a User ID at the top.");
      return;
    }

    if (!transaction.amount || transaction.amount === 0) {
      setError("Please enter an amount.");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/transactions/log`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          transaction: {
            ...transaction,
            date: transaction.date || today,
            amount: transaction.transaction_type === "expense"
              ? -Math.abs(transaction.amount)
              : Math.abs(transaction.amount),
          },
          openaiKey,
          memoriKey,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save transaction");
      }
      setSuccess("Transaction saved and logged in Memori!");
      setTransaction({
        date: today,
        amount: 0,
        category: "Other",
        transaction_type: "expense",
      });
      await loadTransactions();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>💰 Log Transaction</h2>
      <form className="profile-form" onSubmit={onSubmit}>
        <div className="two-column">
          <div className="column">
            <label>
              Date
              <input
                type="date"
                value={transaction.date || today}
                onChange={(e) => handleChange("date", e.target.value)}
              />
            </label>
            <label>
              Transaction Type
              <select
                value={transaction.transaction_type}
                onChange={(e) => handleChange("transaction_type", e.target.value)}
              >
                <option value="expense">Expense</option>
                <option value="income">Income</option>
              </select>
            </label>
            <label>
              Amount ({transaction.transaction_type === "expense" ? "-" : "+"})
              <input
                type="number"
                step="0.01"
                value={transaction.amount || ""}
                placeholder="0.00"
                onChange={(e) => handleChange("amount", e.target.value ? parseFloat(e.target.value) : 0)}
                required
              />
            </label>
            <label>
              Category
              <select
                value={transaction.category}
                onChange={(e) => handleChange("category", e.target.value)}
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
              Merchant/Description
              <input
                type="text"
                value={transaction.merchant || ""}
                placeholder="e.g. Starbucks, Amazon, Salary"
                onChange={(e) => handleChange("merchant", e.target.value || undefined)}
              />
            </label>
            <label>
              Payment Method
              <select
                value={transaction.payment_method || ""}
                onChange={(e) => handleChange("payment_method", e.target.value || undefined)}
              >
                <option value="">Select...</option>
                {paymentMethods.map((method) => (
                  <option key={method} value={method}>
                    {method}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <input
                type="checkbox"
                checked={transaction.is_recurring || false}
                onChange={(e) => handleChange("is_recurring", e.target.checked)}
              />
              Is this a recurring expense?
            </label>
            <label>
              Notes (optional)
              <textarea
                value={transaction.notes || ""}
                placeholder="Additional notes..."
                onChange={(e) => handleChange("notes", e.target.value || undefined)}
                rows={3}
              />
            </label>
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="primary" disabled={saving || !userId}>
            {saving ? "Saving…" : "Log Transaction"}
          </button>
        </div>
      </form>

      {error && <div className="banner error">{error}</div>}
      {success && <div className="banner success">{success}</div>}

      <section style={{ marginTop: "2rem" }}>
        <h3>Recent Transactions</h3>
        {loading ? (
          <p>Loading...</p>
        ) : transactions.length === 0 ? (
          <p>No transactions yet. Log your first transaction above!</p>
        ) : (
          <div className="transaction-list">
            {transactions.map((t) => (
              <div key={t.id} className="transaction-item">
                <div className="transaction-main">
                  <span className="transaction-merchant">{t.merchant || t.category}</span>
                  <span className={`transaction-amount ${t.amount >= 0 ? "income" : "expense"}`}>
                    {t.amount >= 0 ? "+" : ""}{t.amount.toFixed(2)}
                  </span>
                </div>
                <div className="transaction-details">
                  <span className="transaction-category">{t.category}</span>
                  <span className="transaction-date">{new Date(t.date).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default TransactionTab;
