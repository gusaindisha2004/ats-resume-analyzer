"use client";

import { formatDate } from "@/lib/utils";

/**
 * Renders a timestamp in the viewer's local timezone.
 *
 * The server and the browser are in different timezones more often than not,
 * so this text legitimately differs between the SSR pass and hydration.
 * `suppressHydrationWarning` tells React that's intended — without it, every
 * server-rendered date is a hydration error.
 */
export function LocalTime({ iso }: { iso: string }) {
  return (
    <time dateTime={iso} suppressHydrationWarning>
      {formatDate(iso)}
    </time>
  );
}
