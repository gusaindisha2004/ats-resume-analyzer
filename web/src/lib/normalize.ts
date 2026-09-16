import type { AnalysisResponse, ComponentScores } from "@/lib/types";

const ZERO_SCORES: ComponentScores = {
  formatting: 0,
  keywords: 0,
  content: 0,
  skill_validation: 0,
  ats_compatibility: 0,
};

const DEFAULT_MAX = {
  formatting: 20,
  keywords: 25,
  content: 25,
  skill_validation: 15,
  ats_compatibility: 15,
};

/**
 * Fill in anything a stored analysis is missing.
 *
 * History rows are JSON written by whichever version of the app was deployed
 * at the time, so an older row can lack fields the UI now reads. The backend
 * normalises what it can, but passes rows through untouched when they fail
 * validation — so this is the second line of defence. Rendering a section as
 * empty is always better than a blank page.
 */
export function normalizeAnalysis(
  raw: Partial<AnalysisResponse> | null | undefined,
): AnalysisResponse {
  const a = raw ?? {};
  return {
    ats_score: a.ats_score ?? 0,
    interpretation: a.interpretation ?? "",
    component_scores: { ...ZERO_SCORES, ...(a.component_scores ?? {}) },
    component_max: { ...DEFAULT_MAX, ...(a.component_max ?? {}) },
    base_score: a.base_score ?? a.ats_score ?? 0,
    adjustments: a.adjustments ?? [],
    strengths: a.strengths ?? [],
    issues_summary: a.issues_summary ?? [],
    detailed_feedback: a.detailed_feedback ?? [],
    skill_validation: a.skill_validation ?? {
      validated: [],
      unvalidated: [],
      total: 0,
      validated_count: 0,
      validation_pct: 0,
    },
    grammar: a.grammar ?? {
      total_errors: 0,
      score: 100,
      critical: [],
      moderate: [],
      minor: [],
    },
    jd_match: a.jd_match ?? null,
    skills: a.skills ?? [],
    experience_months: a.experience_months ?? 0,
    filename: a.filename ?? "resume",
    analyzed_at: a.analyzed_at ?? new Date(0).toISOString(),
  };
}
