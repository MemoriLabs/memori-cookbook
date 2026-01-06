export type WellnessProfile = {
  name: string;
  age?: number;
  gender?: string;
  primary_goals: string[];
  health_conditions: string[];
  activity_level: string;
  time_commitment: string;
  preferences: string[];
};

export type DailyHabitEntry = {
  date: string;
  sleep_hours?: number;
  sleep_quality?: number;
  exercise_type?: string;
  exercise_duration_minutes?: number;
  exercise_intensity?: string;
  steps?: number;
  water_intake_liters?: number;
  calories_consumed?: number;
  mood_score?: number;
  energy_level?: number;
  stress_level?: number;
  notes?: string;
};

export type WellnessMessage = {
  role: "user" | "assistant";
  content: string;
};
