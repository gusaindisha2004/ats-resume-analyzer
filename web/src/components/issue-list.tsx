"use client";

import { useState } from "react";
import { ChevronDown, CircleAlert, CircleDot, Info } from "lucide-react";
import type { IssueDetail, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const SEVERITY: Record<
  Severity,
  { tone: "weak" | "fair" | "neutral"; icon: typeof CircleAlert; rank: number }
> = {
  High: { tone: "weak", icon: CircleAlert, rank: 0 },
  Moderate: { tone: "fair", icon: CircleDot, rank: 1 },
  Low: { tone: "neutral", icon: Info, rank: 2 },
};

function severityOf(issue: IssueDetail) {
  return SEVERITY[issue.severity_level] ?? SEVERITY.Low;
}

function Issue({ issue }: { issue: IssueDetail }) {
  const [open, setOpen] = useState(false);
  const { tone, icon: Icon } = severityOf(issue);

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-muted"
      >
        <Icon
          className={cn(
            "size-4 shrink-0",
            tone === "weak" && "text-rose-500",
            tone === "fair" && "text-amber-500",
            tone === "neutral" && "text-muted-foreground",
          )}
          aria-hidden
        />
        <span className="min-w-0 flex-1 text-sm font-medium">
          {issue.issue_title}
        </span>
        <Badge tone={tone}>{issue.severity_level}</Badge>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-180",
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div className="space-y-4 border-t border-border bg-surface-muted/50 px-4 py-4 text-sm">
          <p className="text-muted-foreground">{issue.explanation}</p>

          {issue.where_it_appears && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Where it appears
              </h4>
              <p>{issue.where_it_appears}</p>
            </div>
          )}

          {issue.how_to_fix && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                How to fix it
              </h4>
              <p>{issue.how_to_fix}</p>
            </div>
          )}

          {issue.action_items.length > 0 && (
            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Action items
              </h4>
              <ul className="space-y-1.5">
                {issue.action_items.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="mt-1.5 size-1 shrink-0 rounded-full bg-primary" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {issue.example_improvement && (
            <div>
              <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Example
              </h4>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-surface p-3 font-mono text-xs leading-relaxed">
                {issue.example_improvement}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function IssueList({ issues }: { issues: IssueDetail[] }) {
  const sorted = [...issues].sort(
    (a, b) => severityOf(a).rank - severityOf(b).rank,
  );
  const highCount = sorted.filter((i) => i.severity_level === "High").length;

  return (
    <Card>
      <CardHeader
        title="What to fix"
        description={
          sorted.length === 0
            ? "Nothing flagged — this resume parses cleanly."
            : `${sorted.length} issue${sorted.length === 1 ? "" : "s"} found${
                highCount ? `, ${highCount} high severity` : ""
              }.`
        }
      />
      <CardBody className="space-y-2">
        {sorted.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No issues detected. Nice work.
          </p>
        ) : (
          sorted.map((issue, i) => <Issue key={i} issue={issue} />)
        )}
      </CardBody>
    </Card>
  );
}
