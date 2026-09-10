import type { Metadata } from "next";
import { AnalyzeClient } from "@/app/analyze/analyze-client";

export const metadata: Metadata = { title: "Analyze" };

export default function AnalyzePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">
          Analyze a resume
        </h1>
        <p className="mt-2 text-muted-foreground">
          Upload a PDF or DOCX. Add the job posting to unlock match analysis.
        </p>
      </div>
      <AnalyzeClient />
    </div>
  );
}
