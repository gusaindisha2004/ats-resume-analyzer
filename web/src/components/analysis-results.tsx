"use client";

import { useState } from "react";
import { Check, Download, FileText, Loader2 } from "lucide-react";
import type { AnalysisResponse } from "@/lib/types";
import { ApiError, downloadReport } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ScoreGauge } from "@/components/score-gauge";
import { ScoreBreakdown } from "@/components/score-breakdown";
import { IssueList } from "@/components/issue-list";
import { SkillValidationPanel } from "@/components/skill-validation-panel";
import { JDMatchPanel } from "@/components/jd-match-panel";

function DownloadButton({ analysis }: { analysis: AnalysisResponse }) {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function handleDownload() {
    setState("loading");
    setMessage(null);
    try {
      const blob = await downloadReport(analysis);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ats-report-${analysis.filename.replace(/\.[^.]+$/, "")}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
      setState("idle");
    } catch (err) {
      setState("error");
      // A 503 means the server is missing WeasyPrint's native libraries —
      // worth saying out loud rather than showing a bare "failed".
      setMessage(
        err instanceof ApiError
          ? err.message
          : "Could not generate the PDF. Try again.",
      );
    }
  }

  return (
    <div className="w-full">
      <Button
        variant="outline"
        size="sm"
        onClick={handleDownload}
        disabled={state === "loading"}
      >
        {state === "loading" ? (
          <Loader2 className="size-4 animate-spin" aria-hidden />
        ) : (
          <Download className="size-4" aria-hidden />
        )}
        {state === "error" ? "Retry PDF" : "PDF report"}
      </Button>
      {message && (
        <p
          role="alert"
          className="mt-2 max-w-xs text-xs text-rose-700 dark:text-rose-400"
        >
          {message}
        </p>
      )}
    </div>
  );
}

function Strengths({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <Card>
      <CardHeader
        title="What's working"
        description="Keep these when you rewrite."
      />
      <CardBody>
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2.5 text-sm">
              <Check
                className="mt-0.5 size-4 shrink-0 text-emerald-500"
                aria-hidden
              />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function AnalysisResults({ analysis }: { analysis: AnalysisResponse }) {
  return (
    <div className="space-y-6">
      {/* Headline ------------------------------------------------------- */}
      <Card className="overflow-hidden">
        <CardBody className="flex flex-col items-center gap-8 py-8 sm:flex-row sm:items-center sm:justify-center sm:gap-12">
          <ScoreGauge score={analysis.ats_score} />

          <div className="max-w-sm text-center sm:text-left">
            <p className="text-lg font-medium">{analysis.interpretation}</p>

            <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Skills found</dt>
                <dd className="font-medium tabular-nums">
                  {analysis.skill_validation.total}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Experience</dt>
                <dd className="font-medium tabular-nums">
                  {formatDuration(analysis.experience_months)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Issues found</dt>
                <dd className="font-medium tabular-nums">
                  {analysis.detailed_feedback.length}
                </dd>
              </div>
              {analysis.jd_match && (
                <div>
                  <dt className="text-xs text-muted-foreground">JD match</dt>
                  <dd className="font-medium tabular-nums">
                    {Math.round(analysis.jd_match.match_percentage)}%
                  </dd>
                </div>
              )}
            </dl>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
              <DownloadButton analysis={analysis} />
            </div>
          </div>
        </CardBody>

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-border bg-surface-muted/50 px-5 py-2.5 text-xs text-muted-foreground">
          <FileText className="size-3.5" aria-hidden />
          <span className="font-medium text-foreground">{analysis.filename}</span>
          <span aria-hidden>·</span>
          <span>analyzed {formatDate(analysis.analyzed_at)}</span>
        </div>
      </Card>

      {/* Detail --------------------------------------------------------- */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ScoreBreakdown
          scores={analysis.component_scores}
          max={analysis.component_max}
        />
        <Strengths items={analysis.strengths} />
      </div>

      {analysis.jd_match && <JDMatchPanel data={analysis.jd_match} />}

      <IssueList issues={analysis.detailed_feedback} />

      <SkillValidationPanel data={analysis.skill_validation} />
    </div>
  );
}
