import { Check, X } from "lucide-react";
import type { SkillValidation } from "@/lib/types";
import { BAND_CLASSES, cn, scoreBand } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/card";

/**
 * The differentiating feature of this app: every skill claimed in the Skills
 * section is checked against the projects and experience bullets, so an
 * unbacked claim is visible rather than silently counted.
 */
export function SkillValidationPanel({ data }: { data: SkillValidation }) {
  const band = scoreBand(data.validation_pct);

  if (data.total === 0) {
    return (
      <Card>
        <CardHeader title="Skill validation" />
        <CardBody>
          <p className="py-4 text-center text-sm text-muted-foreground">
            No skills were detected on this resume.
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Skill validation"
        description="Skills you claim, checked against the evidence in your projects and experience."
        action={
          <div className="shrink-0 text-right">
            <div
              className={cn(
                "text-2xl font-semibold tabular-nums",
                BAND_CLASSES[band].text,
              )}
            >
              {Math.round(data.validation_pct)}%
            </div>
            <div className="text-xs text-muted-foreground">
              {data.validated_count} of {data.total} backed
            </div>
          </div>
        }
      />
      <CardBody className="space-y-6">
        {data.validated.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
              <Check className="size-3.5" aria-hidden />
              Backed by evidence ({data.validated.length})
            </h3>
            <ul className="space-y-2">
              {data.validated.map((entry) => (
                <li
                  key={entry.skill}
                  className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm"
                >
                  <span className="font-medium">{entry.skill}</span>
                  <span className="text-muted-foreground">
                    — {entry.projects.join(", ") || "experience section"}
                  </span>
                  {entry.similarity !== null && entry.similarity < 1 && (
                    <span className="text-xs tabular-nums text-muted-foreground opacity-70">
                      {Math.round(entry.similarity * 100)}% match
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {data.unvalidated.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-rose-700 dark:text-rose-400">
              <X className="size-3.5" aria-hidden />
              No supporting evidence ({data.unvalidated.length})
            </h3>
            <p className="mb-3 text-sm text-muted-foreground">
              Listed as skills but never mentioned in a project or experience
              bullet. Either demonstrate them or drop them.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {data.unvalidated.map((skill) => (
                <span
                  key={skill}
                  className="rounded-md border border-dashed border-rose-300 px-2 py-1 text-xs text-rose-700 dark:border-rose-900 dark:text-rose-400"
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
