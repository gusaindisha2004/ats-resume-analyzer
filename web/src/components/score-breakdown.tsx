import {
  COMPONENT_META,
  type ComponentKey,
  type ComponentScores,
  type ScoreAdjustment,
} from "@/lib/types";
import { BAND_CLASSES, cn, scoreBand } from "@/lib/utils";
import { Card, CardBody, CardHeader } from "@/components/ui/card";

function Row({
  label,
  blurb,
  score,
  max,
  delay,
}: {
  label: string;
  blurb: string;
  score: number;
  max: number;
  delay: number;
}) {
  const pct = max > 0 ? (score / max) * 100 : 0;
  const band = scoreBand(pct);

  return (
    <div className="animate-rise" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-baseline justify-between gap-4">
        <div className="min-w-0">
          <span className="text-sm font-medium">{label}</span>
          <p className="truncate text-xs text-muted-foreground">{blurb}</p>
        </div>
        <span className="shrink-0 text-sm tabular-nums text-muted-foreground">
          <span className={cn("font-semibold", BAND_CLASSES[band].text)}>
            {score.toFixed(1)}
          </span>
          <span className="opacity-60"> / {max}</span>
        </span>
      </div>

      <div
        className="mt-2 h-2 overflow-hidden rounded-full bg-surface-muted"
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-700 ease-out",
            band === "strong" && "bg-emerald-500",
            band === "fair" && "bg-amber-500",
            band === "weak" && "bg-rose-500",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function ScoreBreakdown({
  scores,
  max,
  baseScore,
  adjustments = [],
  total,
}: {
  scores: ComponentScores;
  max: Record<ComponentKey, number>;
  baseScore?: number;
  adjustments?: ScoreAdjustment[];
  total?: number;
}) {
  // The component maxima are the weights, so the five scores add to the base.
  const summed =
    baseScore ??
    COMPONENT_META.reduce((acc, meta) => acc + scores[meta.key], 0);

  return (
    <Card>
      <CardHeader
        title="Score breakdown"
        description="Where the points came from, and where they leaked."
      />
      <CardBody className="space-y-5">
        {COMPONENT_META.map((meta, i) => (
          <Row
            key={meta.key}
            label={meta.label}
            blurb={meta.blurb}
            score={scores[meta.key]}
            max={max[meta.key]}
            delay={i * 60}
          />
        ))}

        {/* Reconciliation. Without this the five rows above wouldn't visibly
            account for the headline number, which is exactly the criticism
            the old two-layer weighting deserved. */}
        <div className="space-y-2 border-t border-border pt-4 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Component total</span>
            <span className="tabular-nums font-medium">
              {summed.toFixed(1)} / 100
            </span>
          </div>

          {adjustments.map((item) => (
            <div key={item.label} className="flex justify-between gap-4">
              <span className="min-w-0 text-muted-foreground">
                {item.label}
                <span className="block text-xs opacity-70">{item.reason}</span>
              </span>
              <span
                className={cn(
                  "shrink-0 tabular-nums font-medium",
                  item.points >= 0
                    ? "text-emerald-700 dark:text-emerald-400"
                    : "text-rose-700 dark:text-rose-400",
                )}
              >
                {item.points > 0 ? "+" : ""}
                {item.points.toFixed(1)}
              </span>
            </div>
          ))}

          {total !== undefined && (
            <div className="flex justify-between border-t border-border pt-2 font-semibold">
              <span>Overall score</span>
              <span className="tabular-nums">{total.toFixed(1)}</span>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
