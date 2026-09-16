import { describe, expect, it } from "vitest";
import { normalizeAnalysis } from "@/lib/normalize";
import type { AnalysisResponse } from "@/lib/types";

/**
 * History rows are JSON written by whichever version of the app was deployed
 * when they were saved. The UI reads nested fields off them, so a row missing
 * one blanks the page — this is the guard against that.
 */
describe("normalizeAnalysis", () => {
  it("fills every field when given nothing at all", () => {
    const result = normalizeAnalysis(null);

    expect(result.ats_score).toBe(0);
    expect(result.strengths).toEqual([]);
    expect(result.detailed_feedback).toEqual([]);
    expect(result.jd_match).toBeNull();
  });

  it("supplies a grammar report for rows saved before the field existed", () => {
    // The exact regression: reading `.score` off undefined threw.
    const old = { ats_score: 70 } as Partial<AnalysisResponse>;
    const result = normalizeAnalysis(old);

    expect(result.grammar).toBeDefined();
    expect(result.grammar.score).toBe(100);
    expect(result.grammar.critical).toEqual([]);
    expect(() => result.grammar.score.toFixed(0)).not.toThrow();
  });

  it("supplies a skill_validation block when absent", () => {
    const result = normalizeAnalysis({ ats_score: 50 });

    expect(result.skill_validation.total).toBe(0);
    expect(result.skill_validation.validated).toEqual([]);
  });

  it("keeps values that are present", () => {
    const result = normalizeAnalysis({
      ats_score: 83,
      interpretation: "Great!",
      skills: ["Python", "FastAPI"],
      experience_months: 36,
      filename: "alex.pdf",
    });

    expect(result.ats_score).toBe(83);
    expect(result.interpretation).toBe("Great!");
    expect(result.skills).toEqual(["Python", "FastAPI"]);
    expect(result.experience_months).toBe(36);
    expect(result.filename).toBe("alex.pdf");
  });

  it("merges partial component scores over the zeroed defaults", () => {
    const result = normalizeAnalysis({
      component_scores: { keywords: 19 } as never,
    });

    expect(result.component_scores.keywords).toBe(19);
    expect(result.component_scores.formatting).toBe(0);
  });

  it("provides component maxima so the UI can render x / y", () => {
    const result = normalizeAnalysis({});

    expect(result.component_max.keywords).toBe(25);
    expect(result.component_max.formatting).toBe(20);
    expect(result.component_max.ats_compatibility).toBe(15);
  });

  it("returns an analyzed_at that Date can parse", () => {
    const result = normalizeAnalysis({});

    expect(Number.isNaN(new Date(result.analyzed_at).getTime())).toBe(false);
  });

  it("preserves a jd_match when one is present", () => {
    const result = normalizeAnalysis({
      jd_match: {
        match_percentage: 58,
        semantic_similarity: 0.61,
        matched_keywords: ["Python"],
        missing_keywords: ["Kafka"],
        skills_gap: [],
      },
    });

    expect(result.jd_match?.match_percentage).toBe(58);
    expect(result.jd_match?.matched_keywords).toEqual(["Python"]);
  });
});
