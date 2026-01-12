import React, { useState } from "react";
import { WellnessProfile } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  profile: WellnessProfile;
  onSave: (profile: WellnessProfile) => void;
  openaiKey?: string;
  memoriKey?: string;
};

const activityLevelOptions = ["Sedentary", "Light", "Moderate", "Active", "Very Active"];

function ProfileTab({
  apiBase,
  userId,
  profile,
  onSave,
  openaiKey,
  memoriKey
}: Props) {
  const [localProfile, setLocalProfile] = useState<WellnessProfile>(profile);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = <K extends keyof WellnessProfile>(key: K, value: WellnessProfile[K]) => {
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

    const required = localProfile.name && localProfile.primary_goals.length > 0;

    if (!required) {
      setError("Please fill in at least your name and primary wellness goals.");
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

  const goalsText = localProfile.primary_goals.join(", ");
  const conditionsText = localProfile.health_conditions.join(", ");
  const preferencesText = localProfile.preferences.join(", ");

  return (
    <div className="tab-panel">
      <h2>👤 Wellness Profile</h2>
      <form className="profile-form" onSubmit={onSubmit}>
        <div className="two-column">
          <div className="column">
            <label>
              Name or handle
              <input
                type="text"
                value={localProfile.name}
                placeholder="e.g. WellnessUser"
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
              Gender (optional)
              <input
                type="text"
                value={localProfile.gender || ""}
                placeholder="e.g. Male, Female, Non-binary"
                onChange={(e) => handleChange("gender", e.target.value || undefined)}
              />
            </label>
          </div>
          <div className="column">
            <label>
              Activity level
              <select
                value={localProfile.activity_level}
                onChange={(e) => handleChange("activity_level", e.target.value)}
              >
                {activityLevelOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Time commitment
              <input
                type="text"
                value={localProfile.time_commitment}
                placeholder="e.g. 30 minutes/day"
                onChange={(e) => handleChange("time_commitment", e.target.value)}
              />
            </label>
          </div>
        </div>

        <label>
          Primary wellness goals (comma-separated)
          <input
            type="text"
            value={goalsText}
            placeholder="e.g. Better sleep, Weight loss, Stress reduction"
            onChange={(e) =>
              handleChange(
                "primary_goals",
                e.target.value
                  .split(",")
                  .map((g) => g.trim())
                  .filter(Boolean)
              )
            }
          />
        </label>

        <label>
          Health conditions or concerns (comma-separated, optional)
          <input
            type="text"
            value={conditionsText}
            placeholder="e.g. Insomnia, High stress"
            onChange={(e) =>
              handleChange(
                "health_conditions",
                e.target.value
                  .split(",")
                  .map((c) => c.trim())
                  .filter(Boolean)
              )
            }
          />
        </label>

        <label>
          Wellness preferences (comma-separated, optional)
          <input
            type="text"
            value={preferencesText}
            placeholder="e.g. Yoga, Running, Meditation"
            onChange={(e) =>
              handleChange(
                "preferences",
                e.target.value
                  .split(",")
                  .map((p) => p.trim())
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
