import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchEnabledProviders } from "@/lib/auth-providers";

const ORIGINAL_ENV = { ...process.env };

describe("fetchEnabledProviders", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key";
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  function respondWith(external: Record<string, boolean>, ok = true) {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok,
        json: async () => ({ external }),
      }),
    );
  }

  it("reports google as enabled when the project says so", async () => {
    respondWith({ email: true, google: true });
    expect(await fetchEnabledProviders()).toContain("google");
  });

  it("omits google when the project has it turned off", async () => {
    // The exact case that sent the user to a raw Supabase error page.
    respondWith({ email: true, google: false });
    expect(await fetchEnabledProviders()).not.toContain("google");
  });

  it("omits google when the response has no external block", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }),
    );
    expect((await fetchEnabledProviders()).size).toBe(0);
  });

  it("returns nothing when the settings call fails", async () => {
    respondWith({ google: true }, false);
    expect((await fetchEnabledProviders()).size).toBe(0);
  });

  it("returns nothing when the network throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect((await fetchEnabledProviders()).size).toBe(0);
  });

  it("returns nothing when Supabase isn't configured", async () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    expect((await fetchEnabledProviders()).size).toBe(0);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
