import { COMPONENT_META, type ComponentScores, type ComponentKey } from "@/lib/types";
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
}: {
  scores: ComponentScores;
  max: Record<ComponentKey, number>;
}) {
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
      </CardBody>
    </Card>
  );
}
