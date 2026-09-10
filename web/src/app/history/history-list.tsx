"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, Loader2, Trash2 } from "lucide-react";
import { deleteHistoryEntry } from "@/lib/api";
import type { HistoryEntry } from "@/lib/types";
import { BAND_CLASSES, cn, scoreBand } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LocalTime } from "@/components/ui/local-time";
import { AnalysisResults } from "@/components/analysis-results";

function Row({
  entry,
  onDeleted,
}: {
  entry: HistoryEntry;
  onDeleted: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const band = scoreBand(entry.ats_score);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteHistoryEntry(entry.id);
      onDeleted(entry.id);
    } catch (err) {
      setDeleting(false);
      setError(err instanceof Error ? err.message : "Could not delete.");
    }
  }

  return (
    <Card>
      <div className="flex items-center gap-3 px-4 py-3">
        <div
          className={cn(
            "grid size-11 shrink-0 place-items-center rounded-lg text-sm font-semibold tabular-nums ring-1 ring-inset",
            BAND_CLASSES[band].bg,
            BAND_CLASSES[band].text,
            BAND_CLASSES[band].ring,
          )}
        >
          {Math.round(entry.ats_score)}
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{entry.filename}</p>
          <p className="text-xs text-muted-foreground">
            <LocalTime iso={entry.created_at} />
          </p>
          {error && (
            <p role="alert" className="text-xs text-rose-600 dark:text-rose-400">
              {error}
            </p>
          )}
        </div>

        {entry.jd_match_percentage !== null && (
          <Badge tone={scoreBand(entry.jd_match_percentage)}>
            {Math.round(entry.jd_match_percentage)}% JD match
          </Badge>
        )}

        {entry.analysis && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            {open ? "Hide" : "View"}
            <ChevronDown
              className={cn("size-4 transition-transform", open && "rotate-180")}
              aria-hidden
            />
          </Button>
        )}

        <Button
          variant="danger"
          size="icon"
          onClick={handleDelete}
          disabled={deleting}
          aria-label={`Delete analysis of ${entry.filename}`}
        >
          {deleting ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Trash2 className="size-4" aria-hidden />
          )}
        </Button>
      </div>

      {open && entry.analysis && (
        <div className="border-t border-border bg-surface-muted/30 p-4">
          <AnalysisResults analysis={entry.analysis} />
        </div>
      )}
    </Card>
  );
}

export function HistoryList({ entries }: { entries: HistoryEntry[] }) {
  const router = useRouter();
  // Seeded from the server render; deletions drop rows optimistically and then
  // refresh so the server stays the source of truth.
  const [removed, setRemoved] = useState<Set<string>>(new Set());

  const visible = entries.filter((entry) => !removed.has(entry.id));

  function handleDeleted(id: string) {
    setRemoved((current) => new Set(current).add(id));
    router.refresh();
  }

  if (visible.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        Nothing left in your history.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {visible.map((entry) => (
        <Row key={entry.id} entry={entry} onDeleted={handleDeleted} />
      ))}
    </div>
  );
}
