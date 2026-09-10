import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Score band drives every colour decision in the UI — keep it in one place. */
export type Band = "strong" | "fair" | "weak";

export function scoreBand(pct: number): Band {
  if (pct >= 80) return "strong";
  if (pct >= 60) return "fair";
  return "weak";
}

export const BAND_CLASSES: Record<Band, { text: string; bg: string; ring: string; stroke: string }> = {
  strong: {
    text: "text-emerald-700 dark:text-emerald-400",
    bg: "bg-emerald-50 dark:bg-emerald-950/40",
    ring: "ring-emerald-200 dark:ring-emerald-900",
    stroke: "stroke-emerald-500",
  },
  fair: {
    text: "text-amber-700 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-950/40",
    ring: "ring-amber-200 dark:ring-amber-900",
    stroke: "stroke-amber-500",
  },
  weak: {
    text: "text-rose-700 dark:text-rose-400",
    bg: "bg-rose-50 dark:bg-rose-950/40",
    ring: "ring-rose-200 dark:ring-rose-900",
    stroke: "stroke-rose-500",
  },
};

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function formatDuration(months: number): string {
  if (months <= 0) return "—";
  const years = Math.floor(months / 12);
  const rest = months % 12;
  if (!years) return `${rest} mo`;
  if (!rest) return `${years} yr`;
  return `${years} yr ${rest} mo`;
}
