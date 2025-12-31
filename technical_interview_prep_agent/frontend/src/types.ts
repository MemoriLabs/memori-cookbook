export type CandidateProfile = {
  name: string;
  target_role: string;
  experience_level: string;
  primary_language: string;
  target_companies: string[];
  main_goal: string;
  timeframe: string;
};

export type ProblemMetadata = {
  title: string;
  difficulty: string;
  patterns: string[];
  statement: string;
};

export type ProgressMessage = {
  role: "user" | "assistant";
  content: string;
};
