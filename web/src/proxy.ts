import type { NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

/**
 * Runs before every matched request: refreshes the Supabase session cookie and
 * redirects signed-out visitors away from the app routes.
 *
 * This is an *optimistic* check only — per the Next.js docs, proxy is not an
 * authorization layer. Real enforcement happens on the FastAPI side, which
 * verifies the Supabase JWT on every request and scopes each query by user id.
 */
export async function proxy(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    // Everything except static assets and image files.
    "/((?!_next/static|_next/image|favicon.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
