"use client";

import { useState } from "react";
import { RotateCcw } from "lucide-react";
import type { AnalysisResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { UploadForm } from "@/components/upload-form";
import { AnalysisResults } from "@/components/analysis-results";

export function AnalyzeClient() {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);

  if (!analysis) return <UploadForm onComplete={setAnalysis} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={() => setAnalysis(null)}>
          <RotateCcw className="size-4" aria-hidden />
          Analyze another
        </Button>
      </div>
      <AnalysisResults analysis={analysis} />
    </div>
  );
}
