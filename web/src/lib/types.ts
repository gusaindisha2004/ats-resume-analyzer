/**
 * Mirrors backend/models/schemas.py. If you rename a field there, rename it here.
 */

export interface ComponentScores {
  formatting: number;
  keywords: number;
  content: number;
  skill_validation: number;
  ats_compatibility: number;
}

export type ComponentKey = keyof ComponentScores;

export interface JDMatch {
  match_percentage: number;
  semantic_similarity: number;
  matched_keywords: string[];
  missing_keywords: string[];
  skills_gap: string[];
}

export interface ValidatedSkill {
  skill: string;
  projects: string[];
  similarity: number | null;
}

export interface SkillValidation {
  validated: ValidatedSkill[];
  unvalidated: string[];
  total: number;
  validated_count: number;
  validation_pct: number;
}

export type Severity = "High" | "Moderate" | "Low";

export interface IssueDetail {
  issue_title: string;
  severity_level: Severity;
  ats_impact: string;
  explanation: string;
  where_it_appears: string;
  how_to_fix: string;
  action_items: string[];
  example_improvement: string;
}

export interface AnalysisResponse {
  ats_score: number;
  interpretation: string;
  component_scores: ComponentScores;
  component_max: Record<ComponentKey, number>;

  strengths: string[];
  issues_summary: string[];
  detailed_feedback: IssueDetail[];

  skill_validation: SkillValidation;
  jd_match: JDMatch | null;

  skills: string[];
  experience_months: number;

  filename: string;
  analyzed_at: string;
}

export interface HistoryEntry {
  id: string;
  filename: string;
  ats_score: number;
  jd_match_percentage: number | null;
  created_at: string;
  analysis: AnalysisResponse | null;
}

/** Display metadata for each scoring component, in the order we render them. */
export const COMPONENT_META: {
  key: ComponentKey;
  label: string;
  blurb: string;
}[] = [
  {
    key: "keywords",
    label: "Keywords & Skills",
    blurb: "Coverage of the terms an ATS filters on",
  },
  {
    key: "content",
    label: "Content Quality",
    blurb: "Action verbs and quantified achievements",
  },
  {
    key: "formatting",
    label: "Formatting",
    blurb: "Section structure and consistent bullets",
  },
  {
    key: "skill_validation",
    label: "Skill Validation",
    blurb: "Claimed skills backed by real evidence",
  },
  {
    key: "ats_compatibility",
    label: "ATS Compatibility",
    blurb: "How cleanly a parser can read the file",
  },
];
