import React, { useState, useEffect } from "react";
import { DailyHabitEntry } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  openaiKey?: string;
  memoriKey?: string;
};

function DailyLogTab({ apiBase, userId, openaiKey, memoriKey }: Props) {
  const [today, setToday] = useState(new Date().toISOString().split("T")[0]);
  const [entry, setEntry] = useState<DailyHabitEntry>({
    date: today,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [existingEntry, setExistingEntry] = useState<any>(null);

  useEffect(() => {
    if (userId) {
      loadTodayEntry();
    }
  }, [userId, today]);

  const loadTodayEntry = async () => {
    try {
      const res = await fetch(`${apiBase}/habits/${userId}/today`);
      if (res.ok) {
        const data = await res.json();
        if (data.exists && data.habit) {
          const habit = data.habit;
          setEntry({
            date: today,
            sleep_hours: habit.sleep?.hours,
            sleep_quality: habit.sleep?.quality,
            exercise_type: habit.exercise?.type,
            exercise_duration_minutes: habit.exercise?.durationMinutes,
            exercise_intensity: habit.exercise?.intensity,
            steps: habit.exercise?.steps,
            water_intake_liters: habit.nutrition?.waterIntakeLiters,
            calories_consumed: habit.nutrition?.caloriesConsumed,
            mood_score: habit.mood?.score,
            energy_level: habit.mood?.energyLevel,
            stress_level: habit.mood?.stressLevel,
            notes: habit.generalNotes,
          });
          setExistingEntry(data.habit);
        }
      }
    } catch (e) {
      // Ignore errors
    }
  };

  const handleChange = (field: keyof DailyHabitEntry, value: any) => {
    setEntry({ ...entry, [field]: value });
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

    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/habits/log`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          habitEntry: {
            ...entry,
            date: entry.date || today,
          },
          openaiKey,
          memoriKey,
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save habit log");
      }
      const data = await res.json();
      setSuccess(existingEntry ? "Habit log updated!" : "Habit log saved!");
      setExistingEntry(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📝 Daily Habit Log</h2>
      <p style={{ marginBottom: "24px", color: "var(--color-text-secondary)" }}>
        Log your daily habits to track patterns and identify correlations over time.
      </p>

      <form className="profile-form" onSubmit={onSubmit}>
        <div className="form-group">
          <label>
            Date
            <input
              type="date"
              value={entry.date || today}
              onChange={(e) => handleChange("date", e.target.value)}
            />
          </label>
        </div>

        <div className="section-divider">
          <h3>😴 Sleep</h3>
        </div>
        <div className="two-column">
          <div className="column">
            <label>
              Sleep hours
              <input
                type="number"
                step="0.5"
                min="0"
                max="24"
                value={entry.sleep_hours || ""}
                placeholder="e.g. 8.5"
                onChange={(e) => handleChange("sleep_hours", e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </label>
          </div>
          <div className="column">
            <label>
              Sleep quality (1-10)
              <input
                type="number"
                min="1"
                max="10"
                value={entry.sleep_quality || ""}
                placeholder="e.g. 8"
                onChange={(e) => handleChange("sleep_quality", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
          </div>
        </div>

        <div className="section-divider">
          <h3>🏃 Exercise</h3>
        </div>
        <div className="two-column">
          <div className="column">
            <label>
              Exercise type
              <input
                type="text"
                value={entry.exercise_type || ""}
                placeholder="e.g. Running, Yoga, Strength"
                onChange={(e) => handleChange("exercise_type", e.target.value || undefined)}
              />
            </label>
            <label>
              Duration (minutes)
              <input
                type="number"
                min="0"
                value={entry.exercise_duration_minutes || ""}
                placeholder="e.g. 30"
                onChange={(e) => handleChange("exercise_duration_minutes", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
          </div>
          <div className="column">
            <label>
              Intensity
              <select
                value={entry.exercise_intensity || ""}
                onChange={(e) => handleChange("exercise_intensity", e.target.value || undefined)}
              >
                <option value="">Select...</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </label>
            <label>
              Steps
              <input
                type="number"
                min="0"
                value={entry.steps || ""}
                placeholder="e.g. 10000"
                onChange={(e) => handleChange("steps", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
          </div>
        </div>

        <div className="section-divider">
          <h3>🥗 Nutrition</h3>
        </div>
        <div className="two-column">
          <div className="column">
            <label>
              Water intake (liters)
              <input
                type="number"
                step="0.1"
                min="0"
                value={entry.water_intake_liters || ""}
                placeholder="e.g. 2.5"
                onChange={(e) => handleChange("water_intake_liters", e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </label>
          </div>
          <div className="column">
            <label>
              Calories consumed
              <input
                type="number"
                min="0"
                value={entry.calories_consumed || ""}
                placeholder="e.g. 2000"
                onChange={(e) => handleChange("calories_consumed", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
          </div>
        </div>

        <div className="section-divider">
          <h3>😊 Mood & Energy</h3>
        </div>
        <div className="two-column">
          <div className="column">
            <label>
              Mood score (1-10)
              <input
                type="number"
                min="1"
                max="10"
                value={entry.mood_score || ""}
                placeholder="e.g. 8"
                onChange={(e) => handleChange("mood_score", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
            <label>
              Energy level (1-10)
              <input
                type="number"
                min="1"
                max="10"
                value={entry.energy_level || ""}
                placeholder="e.g. 7"
                onChange={(e) => handleChange("energy_level", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
          </div>
          <div className="column">
            <label>
              Stress level (1-10)
              <input
                type="number"
                min="1"
                max="10"
                value={entry.stress_level || ""}
                placeholder="e.g. 3"
                onChange={(e) => handleChange("stress_level", e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </label>
          </div>
        </div>

        <div className="form-group">
          <label>
            Notes (optional)
            <textarea
              value={entry.notes || ""}
              placeholder="Any additional notes about your day..."
              onChange={(e) => handleChange("notes", e.target.value || undefined)}
              rows={3}
            />
          </label>
        </div>

        <div className="form-actions">
          <button type="submit" className="primary" disabled={saving || !userId}>
            {saving ? "Saving…" : existingEntry ? "Update Log" : "Save Log"}
          </button>
        </div>
      </form>

      {error && <div className="banner error">{error}</div>}
      {success && <div className="banner success">{success}</div>}
    </div>
  );
}

export default DailyLogTab;
