import { CircleAlert, CircleDot, Info, SpellCheck } from "lucide-react";
import type { GrammarReport, WritingIssue } from "@/lib/types";
import { BAND_CLASSES, cn, scoreBand } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/card";

const GROUPS = [
  {
    key: "critical" as const,
    label: "Spelling",
    blurb:
      "Misspellings read as carelessness, and a misspelled skill won't match an ATS keyword search.",
    icon: CircleAlert,
    tone: "text-rose-500",
  },
  {
    key: "moderate" as const,
    label: "Writing style",
    blurb:
      "Phrasing that weakens otherwise good bullets — these cost you a screen more often than typos do.",
    icon: CircleDot,
    tone: "text-amber-500",
  },
  {
    key: "minor" as const,
    label: "Polish",
    blurb: "Small consistency issues worth a final pass.",
    icon: Info,
    tone: "text-muted-foreground",
  },
];

function Issue({ issue }: { issue: WritingIssue }) {
  return (
    <li className="text-sm">
      <div className="flex flex-wrap items-baseline gap-x-2">
        <code className="rounded bg-surface-muted px-1.5 py-0.5 font-mono text-xs">
          {issue.error_text}
        </code>
        {issue.suggestions.length > 0 && (
          <span className="text-xs text-muted-foreground">
            → <span className="font-medium text-emerald-700 dark:text-emerald-400">
              {issue.suggestions[0]}
            </span>
          </span>
        )}
      </div>
      <p className="mt-0.5 text-muted-foreground">{issue.message}</p>
      {issue.context && (
        <p className="mt-0.5 truncate text-xs italic text-muted-foreground opacity-70">
          &ldquo;{issue.context}&rdquo;
        </p>
      )}
    </li>
  );
}

export function GrammarPanel({ data }: { data: GrammarReport }) {
  const band = scoreBand(data.score);

  return (
    <Card>
      <CardHeader
        title="Writing quality"
        description="Spelling and resume-specific style, checked against the whole document."
        action={
          <div className="shrink-0 text-right">
            <div
              className={cn(
                "text-2xl font-semibold tabular-nums",
                BAND_CLASSES[band].text,
              )}
            >
              {Math.round(data.score)}
            </div>
            <div className="text-xs text-muted-foreground">
              {data.total_errors === 0
                ? "no issues"
                : `${data.total_errors} issue${data.total_errors === 1 ? "" : "s"}`}
            </div>
          </div>
        }
      />
      <CardBody className="space-y-6">
        {data.total_errors === 0 ? (
          <div className="flex items-center gap-2.5 py-4 text-sm">
            <SpellCheck
              className="size-5 shrink-0 text-emerald-500"
              aria-hidden
            />
            <span>
              No spelling or phrasing problems found. Technology names and
              British spellings are excluded from the check.
            </span>
          </div>
        ) : (
          GROUPS.map(({ key, label, blurb, icon: Icon, tone }) => {
            const issues = data[key];
            if (issues.length === 0) return null;
            return (
              <section key={key}>
                <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  <Icon className={cn("size-3.5", tone)} aria-hidden />
                  {label} ({issues.length})
                </h3>
                <p className="mt-1 mb-3 text-sm text-muted-foreground">
                  {blurb}
                </p>
                <ul className="space-y-3">
                  {issues.map((issue, i) => (
                    <Issue key={`${issue.error_text}-${i}`} issue={issue} />
                  ))}
                </ul>
              </section>
            );
          })
        )}
      </CardBody>
    </Card>
  );
}
