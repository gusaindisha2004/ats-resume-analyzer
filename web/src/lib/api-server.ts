import "server-only";

import type { HistoryEntry } from "@/lib/types";
import { createClient } from "@/lib/supabase/server";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Server-side history fetch. Runs during the render of a Server Component, so
 * the page arrives with data already in it — no client effect, no spinner.
 */
export async function getHistoryServer(): Promise<
  { data: HistoryEntry[]; error: null } | { data: null; error: string }
> {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    return { data: null, error: "You need to be signed in." };
  }

  try {
    const response = await fetch(`${BASE_URL}/api/v1/history`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      return {
        data: null,
        error:
          typeof body?.detail === "string"
            ? body.detail
            : `The API returned ${response.status}.`,
      };
    }

    return { data: (await response.json()) as HistoryEntry[], error: null };
  } catch {
    return {
      data: null,
      error: "Could not reach the analysis service. Is the backend running?",
    };
  }
}
