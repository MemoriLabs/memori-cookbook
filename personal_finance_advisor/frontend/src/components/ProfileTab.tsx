import React, { useState } from "react";
import { FinancialProfile } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  profile: FinancialProfile;
  onSave: (profile: FinancialProfile) => void;
  openaiKey?: string;
  memoriKey?: string;
};

const riskToleranceOptions = ["Conservative", "Moderate", "Aggressive"];

function ProfileTab({
  apiBase,
  userId,
  profile,
  onSave,
  openaiKey,
  memoriKey
}: Props) {
  const [localProfile, setLocalProfile] = useState<FinancialProfile>(profile);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = <K extends keyof FinancialProfile>(key: K, value: FinancialProfile[K]) => {
    setLocalProfile({ ...localProfile, [key]: value });
    setSuccess(null);
    setError(null);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!userId) {
      setError("Please enter a User ID / handle at the top before saving your profile.");
      return;
    }

    const required = localProfile.name;

    if (!required) {
      setError("Please fill in at least your name.");
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile: localProfile,
          openaiKey,
          memoriKey
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save profile");
      }
      await res.json();
      onSave(localProfile);
      setSuccess("Profile saved and stored in Memori.");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const goalsText = localProfile.financial_goals.join(", ");

  return (
    <div className="tab-panel">
      <h2>👤 Financial Profile</h2>
      <form className="profile-form" onSubmit={onSubmit}>
        <div className="two-column">
          <div className="column">
            <label>
              Name or handle
              <input
                type="text"
                value={localProfile.name}
                placeholder="e.g. FinanceUser"
                onChange={(e) => handleChange("name", e.target.value)}
              />
            </label>
            <label>
              Age (optional)
              <input
                type="number"
                value={localProfile.age || ""}
                placeholder="e.g. 30"
                onChange={(e) => handleChange("age", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
            <label>
              Monthly Income (optional)
              <input
                type="number"
                step="0.01"
                value={localProfile.income || ""}
                placeholder="e.g. 5000.00"
                onChange={(e) => handleChange("income", e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </label>
            <label>
              Currency
              <input
                type="text"
                value={localProfile.currency}
                placeholder="USD"
                onChange={(e) => handleChange("currency", e.target.value)}
              />
            </label>
          </div>
          <div className="column">
            <label>
              Risk Tolerance
              <select
                value={localProfile.risk_tolerance}
                onChange={(e) => handleChange("risk_tolerance", e.target.value)}
              >
                {riskToleranceOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Monthly Expenses Estimate (optional)
              <input
                type="number"
                step="0.01"
                value={localProfile.monthly_expenses_estimate || ""}
                placeholder="e.g. 3000.00"
                onChange={(e) => handleChange("monthly_expenses_estimate", e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </label>
            <label>
              Savings Balance (optional)
              <input
                type="number"
                step="0.01"
                value={localProfile.savings_balance || ""}
                placeholder="e.g. 10000.00"
                onChange={(e) => handleChange("savings_balance", e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </label>
            <label>
              Debt Balance (optional)
              <input
                type="number"
                step="0.01"
                value={localProfile.debt_balance || ""}
                placeholder="e.g. 5000.00"
                onChange={(e) => handleChange("debt_balance", e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </label>
          </div>
        </div>

        <label>
          Financial goals (comma-separated)
          <input
            type="text"
            value={goalsText}
            placeholder="e.g. Save for emergency fund, Pay off credit card debt, Save for vacation"
            onChange={(e) =>
              handleChange(
                "financial_goals",
                e.target.value
                  .split(",")
                  .map((g) => g.trim())
                  .filter(Boolean)
              )
            }
          />
        </label>

        <div className="form-actions">
          <button type="submit" className="primary" disabled={saving || !userId}>
            {saving ? "Saving…" : "Save Profile"}
          </button>
        </div>
      </form>

      {error && <div className="banner error">{error}</div>}
      {success && <div className="banner success">{success}</div>}

      {localProfile.name && (
        <section className="current-profile">
          <h3>Current Profile</h3>
          <pre className="profile-json">
{JSON.stringify(localProfile, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

export default ProfileTab;
