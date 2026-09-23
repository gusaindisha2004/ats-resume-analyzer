/**
 * Which OAuth providers this Supabase project actually has enabled.
 *
 * Rendering a "Continue with Google" button for a project where Google is
 * turned off sends the user to a raw Supabase JSON error page — a full browser
 * navigation, so the client can't catch it and show something friendlier.
 * Asking first is the only way to avoid offering a button that cannot work.
 */
export type OAuthProvider = "google";

const SETTINGS_PATH = "/auth/v1/settings";

export async function fetchEnabledProviders(): Promise<Set<OAuthProvider>> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return new Set();

  try {
    const response = await fetch(`${url.replace(/\/$/, "")}${SETTINGS_PATH}`, {
      headers: { apikey: key },
    });
    if (!response.ok) return new Set();

    const body = (await response.json()) as {
      external?: Record<string, boolean>;
    };
    const external = body.external ?? {};

    const enabled = new Set<OAuthProvider>();
    if (external.google) enabled.add("google");
    return enabled;
  } catch {
    // Offline, or the project is unreachable. Hiding the button is the safe
    // default: email sign-in still works.
    return new Set();
  }
}
