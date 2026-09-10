import { BAND_CLASSES, cn, scoreBand } from "@/lib/utils";

const SIZE = 200;
const STROKE = 14;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

// The arc spans 270°, leaving a 90° gap at the bottom for the caption.
const SWEEP = 0.75;
const TRACK_LENGTH = CIRCUMFERENCE * SWEEP;

/**
 * Radial score gauge. Drawn as inline SVG rather than a chart library so it
 * stays sharp at any size and adds nothing to the bundle.
 */
export function ScoreGauge({
  score,
  label = "ATS Score",
  className,
}: {
  score: number;
  label?: string;
  className?: string;
}) {
  const clamped = Math.min(100, Math.max(0, score));
  const band = scoreBand(clamped);
  const filled = TRACK_LENGTH * (clamped / 100);

  return (
    <div className={cn("relative inline-grid place-items-center", className)}>
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={`${label}: ${Math.round(clamped)} out of 100`}
        className="-rotate-[225deg]"
      >
        {/* Track */}
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${TRACK_LENGTH} ${CIRCUMFERENCE}`}
          className="stroke-border"
        />
        {/* Value */}
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
          className={cn(BAND_CLASSES[band].stroke, "animate-gauge")}
          style={{ "--dash-total": `${filled}px` } as React.CSSProperties}
        />
      </svg>

      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div
            className={cn(
              "text-5xl font-semibold tabular-nums tracking-tight",
              BAND_CLASSES[band].text,
            )}
          >
            {Math.round(clamped)}
          </div>
          <div className="mt-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
        </div>
      </div>
    </div>
  );
}
