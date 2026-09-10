import { notFound } from "next/navigation";
import { AnalysisResults } from "@/components/analysis-results";
import type { AnalysisResponse } from "@/lib/types";

// Dev-only design harness: renders the results UI from a fixture so you can
// iterate on layout without a Groq key or a real resume. Not routable in
// production. Safe to delete.

const FIXTURE: AnalysisResponse = {
  ats_score: 71,
  interpretation: "Good! Your resume is ATS-friendly with room for minor improvements.",
  component_scores: {
    formatting: 17.5, keywords: 19, content: 18.5,
    skill_validation: 9, ats_compatibility: 14,
  },
  component_max: {
    formatting: 20, keywords: 25, content: 25,
    skill_validation: 15, ats_compatibility: 15,
  },
  strengths: [
    "Has a dedicated Experience section",
    "Includes a Projects section showcasing applied skills",
    "Uses 8 strong action verbs in bullet points",
    "Content quality is high with measurable achievements",
  ],
  issues_summary: ["Most Skills Lack Supporting Evidence", "Missing Professional Summary"],
  detailed_feedback: [
    {
      issue_title: "Most Skills Lack Supporting Evidence",
      severity_level: "Moderate", ats_impact: "High",
      explanation: "60% of your listed skills (3 out of 5) are not backed by any mention in your projects or experience sections. Recruiters and ATS systems cross-reference skills against actual work to verify credibility.",
      where_it_appears: "These skills have no supporting context: Kubernetes, Terraform, Kafka",
      how_to_fix: "For each skill in your Skills section, ensure it appears at least once in a project description or experience bullet point.",
      action_items: [
        "Mention 'Kubernetes' in a project or experience bullet point",
        "Mention 'Terraform' in a project or experience bullet point",
        "Remove skills you cannot demonstrate with any project or experience",
      ],
      example_improvement: "Fix: Add to a project or experience bullet:\n'Built a data pipeline using Kubernetes that processed 10K records daily, reducing manual effort by 60%.'",
    },
    {
      issue_title: "Missing Professional Summary",
      severity_level: "Low", ats_impact: "Low",
      explanation: "Your resume does not include a Professional Summary at the top. A 2-3 line summary helps recruiters quickly understand your profile.",
      where_it_appears: "Top of resume — below contact info",
      how_to_fix: "Add a 2-3 sentence summary highlighting your experience level, key skills, and career focus.",
      action_items: ["Add a 'PROFESSIONAL SUMMARY' section", "Keep it under 60 words"],
      example_improvement: "PROFESSIONAL SUMMARY\nBackend engineer with 3 years building payment systems using Python, FastAPI and PostgreSQL.",
    },
  ],
  skill_validation: {
    validated: [
      { skill: "Python", projects: ["Ledger Service", "Experience Section"], similarity: 1 },
      { skill: "PostgreSQL", projects: ["Ledger Service"], similarity: 1 },
    ],
    unvalidated: ["Kubernetes", "Terraform", "Kafka"],
    total: 5, validated_count: 2, validation_pct: 40,
  },
  grammar: {
    total_errors: 4,
    score: 78,
    critical: [
      { error_text: "developement", message: "'developement' looks misspelled.", suggestions: ["development"], context: "Responsible for the backend developement" },
      { error_text: "performace", message: "'performace' looks misspelled.", suggestions: ["performance"], context: "improving performace of the system" },
    ],
    moderate: [
      { error_text: "responsible for", message: "'Responsible for' describes a duty, not an achievement. Start with a past-tense action verb instead.", suggestions: [], context: "Responsible for the backend developement" },
      { error_text: "I", message: "Avoid first-person pronouns — drop 'I' and lead with a verb.", suggestions: [], context: "I worked on payment features" },
    ],
    minor: [],
  },
  jd_match: {
    match_percentage: 58.4, semantic_similarity: 0.61,
    matched_keywords: ["Python", "FastAPI", "PostgreSQL", "REST API design"],
    missing_keywords: ["Kubernetes", "Kafka", "distributed systems", "Terraform"],
    skills_gap: ["service mesh", "event streaming"],
  },
  skills: ["Python", "FastAPI", "PostgreSQL", "Kubernetes", "Terraform"],
  experience_months: 36,
  filename: "alex-rivera-resume.pdf",
  analyzed_at: "2026-09-11T09:24:00.000Z",
};

export default function PreviewPage() {
  if (process.env.NODE_ENV === "production") notFound();
  return <AnalysisResults analysis={FIXTURE} />;
}
