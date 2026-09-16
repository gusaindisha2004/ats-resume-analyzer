"use client"; // Error boundaries must be Client Components

import Link from "next/link";
import { RotateCcw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";

/**
 * Route-level error boundary. Catches render and data errors below the root
 * layout so a thrown exception degrades to this instead of a blank page.
 *
 * Uses `retry()` rather than `reset()`: retry re-fetches the boundary's
 * children, which is what recovers a transient backend failure. `reset()` only
 * re-renders, so a failed fetch would fail again immediately.
 */
export default function Error({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg py-16">
      <Card>
        <CardBody className="space-y-4 text-center">
          <TriangleAlert className="mx-auto size-8 text-rose-500" aria-hidden />

          <div>
            <h1 className="text-lg font-semibold">Something went wrong</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              This page hit an unexpected error. Trying again often clears it —
              if the analysis service was restarting, it may just need a moment.
            </p>
          </div>

          {/* The digest matches this error to a line in the server logs. */}
          {error.digest && (
            <p className="font-mono text-xs text-muted-foreground">
              Reference: {error.digest}
            </p>
          )}

          <div className="flex justify-center gap-3 pt-1">
            <Button onClick={() => retry()}>
              <RotateCcw className="size-4" aria-hidden />
              Try again
            </Button>
            <Link
              href="/"
              className="inline-flex h-10 items-center rounded-lg border border-border bg-surface px-4 text-sm font-medium transition-colors hover:border-primary/30 hover:bg-primary-subtle"
            >
              Go home
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
