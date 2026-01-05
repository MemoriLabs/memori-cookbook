import React, { useState } from "react";
import { CandidateProfile } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  profile: CandidateProfile;
  setProfile: (p: CandidateProfile) => void;
  setHasProfile: (v: boolean) => void;
  onProfileUpdated: () => void;
  openaiKey?: string;
  memoriKey?: string;
};

const experienceOptions = ["Student", "Junior", "Mid", "Senior", "Staff", "Other"];
const languageOptions = [
  "Python",
  "Java",
  "C++",
  "JavaScript/TypeScript",
  "Go",
  "Other"
];

function ProfileTab({
  apiBase,
  userId,
  profile,
  setProfile,
  setHasProfile,
  onProfileUpdated,
  openaiKey,
  memoriKey
}: Props) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = <K extends keyof CandidateProfile>(key: K, value: CandidateProfile[K]) => {
    setProfile({ ...profile, [key]: value });
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

    const required =
      profile.name &&
      profile.target_role &&
      profile.experience_level &&
      profile.primary_language &&
      profile.main_goal &&
      profile.timeframe;

    if (!required) {
      setError(
        "Please fill in all required fields (name, role, level, language, goal, timeframe)."
      );
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${apiBase}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          profile: {
            ...profile,
            target_companies: profile.target_companies
          },
          openaiKey,
          memoriKey
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to save profile");
      }
      await res.json();
      setHasProfile(true);
      onProfileUpdated();
      setSuccess("Profile saved and stored in Memori.");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const companiesText = profile.target_companies.join(", ");

  return (
    <div className="tab-panel">
      <h2>🧑‍💻 Candidate Profile &amp; Goals</h2>
      <form className="profile-form" onSubmit={onSubmit}>
        <div className="two-column">
          <div className="column">
            <label>
              Name or handle
              <input
                type="text"
                value={profile.name}
                placeholder="e.g. 3rdSon"
                onChange={(e) => handleChange("name", e.target.value)}
              />
            </label>
            <label>
              Target role
              <input
                type="text"
                value={profile.target_role}
                placeholder="e.g. Backend SWE, ML Engineer"
                onChange={(e) => handleChange("target_role", e.target.value)}
              />
            </label>
            <label>
              Experience level
              <select
                value={profile.experience_level}
                onChange={(e) => handleChange("experience_level", e.target.value)}
              >
                {experienceOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="column">
            <label>
              Primary interview language
              <select
                value={profile.primary_language}
                onChange={(e) => handleChange("primary_language", e.target.value)}
              >
                {languageOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Target companies (comma-separated)
              <input
                type="text"
                value={companiesText}
                placeholder="e.g. Google, Meta, Stripe"
                onChange={(e) =>
                  handleChange(
                    "target_companies",
                    e.target.value
                      .split(",")
                      .map((c) => c.trim())
                      .filter(Boolean)
                  )
                }
              />
            </label>
            <label>
              Timeframe
              <input
                type="text"
                value={profile.timeframe}
                placeholder="e.g. 3 months, 6 weeks"
                onChange={(e) => handleChange("timeframe", e.target.value)}
              />
            </label>
          </div>
        </div>

        <label>
          Main interview goal
          <input
            type="text"
            value={profile.main_goal}
            placeholder="e.g. Crack FAANG interviews in 3 months"
            onChange={(e) => handleChange("main_goal", e.target.value)}
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

      {profile.name && (
        <section className="current-profile">
          <h3>Current Profile</h3>
          <pre className="profile-json">
{JSON.stringify(profile, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

export default ProfileTab;
