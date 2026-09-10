import type { JDMatch } from "@/lib/types";
import { BAND_CLASSES, cn, scoreBand } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/card";

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: number;
  hint: string;
}) {
  const band = scoreBand(value);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span
          className={cn(
            "text-lg font-semibold tabular-nums",
            BAND_CLASSES[band].text,
          )}
        >
          {Math.round(value)}%
        </span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-muted">
        <div
          className={cn(
            "h-full rounded-full",
            band === "strong" && "bg-emerald-500",
            band === "fair" && "bg-amber-500",
            band === "weak" && "bg-rose-500",
          )}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

function KeywordGroup({
  title,
  keywords,
  emptyText,
  variant,
}: {
  title: string;
  keywords: string[];
  emptyText: string;
  variant: "matched" | "missing";
}) {
  return (
    <section>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title} {keywords.length > 0 && `(${keywords.length})`}
      </h3>
      {keywords.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {keywords.map((kw) => (
            <span
              key={kw}
              className={cn(
                "rounded-md px-2 py-1 text-xs ring-1 ring-inset",
                variant === "matched"
                  ? "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-400 dark:ring-emerald-900"
                  : "bg-rose-50 text-rose-700 ring-rose-200 dark:bg-rose-950/50 dark:text-rose-400 dark:ring-rose-900",
              )}
            >
              {kw}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

export function JDMatchPanel({ data }: { data: JDMatch }) {
  return (
    <Card>
      <CardHeader
        title="Job description match"
        description="How this resume reads against the role you pasted in."
      />
      <CardBody className="space-y-6">
        <div className="grid gap-5 sm:grid-cols-2">
          <Metric
            label="Overall match"
            value={data.match_percentage}
            hint="Keyword overlap (60%) blended with semantic similarity (40%)."
          />
          <Metric
            label="Semantic similarity"
            value={data.semantic_similarity * 100}
            hint="How closely the two documents read, independent of exact wording."
          />
        </div>

        <KeywordGroup
          title="Matched keywords"
          keywords={data.matched_keywords}
          emptyText="Nothing from the job description matched yet."
          variant="matched"
        />

        <KeywordGroup
          title="Missing keywords"
          keywords={data.missing_keywords}
          emptyText="Every key term from the posting appears somewhere in your resume."
          variant="missing"
        />

        {data.skills_gap.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Skills gap ({data.skills_gap.length})
            </h3>
            <p className="mb-2 text-sm text-muted-foreground">
              Mentioned in the posting, absent from your resume. Add the ones you
              genuinely have.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {data.skills_gap.map((skill) => (
                <span
                  key={skill}
                  className="rounded-md bg-surface-muted px-2 py-1 text-xs text-muted-foreground ring-1 ring-inset ring-border"
                >
                  {skill}
                </span>
              ))}
            </div>
          </section>
        )}
      </CardBody>
    </Card>
  );
}
