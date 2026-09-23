"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, TriangleAlert } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { fetchEnabledProviders } from "@/lib/auth-providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Mode = "signin" | "signup";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next") ?? "/analyze";

  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  // Null until we know; the button stays hidden in the meantime rather than
  // flashing in and out.
  const [googleEnabled, setGoogleEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    fetchEnabledProviders().then((providers) => {
      if (active) setGoogleEnabled(providers.has("google"));
    });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setNotice(null);

    const supabase = createClient();

    if (mode === "signup") {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback?next=${next}`,
        },
      });
      setPending(false);
      if (error) return setError(error.message);
      // With email confirmation on, Supabase returns a user but no session.
      if (!data.session) {
        return setNotice(
          `Check ${email} for a confirmation link, then sign in.`,
        );
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      setPending(false);
      if (error) {
        return setError(
          error.message === "Invalid login credentials"
            ? "Wrong email or password."
            : error.message,
        );
      }
    }

    router.push(next);
    router.refresh();
  }

  async function handleGoogle() {
    setError(null);
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback?next=${next}`,
      },
    });
    if (error) setError(error.message);
  }

  return (
    <div className="mx-auto max-w-sm py-8">
      <h1 className="text-center text-2xl font-semibold tracking-tight">
        {mode === "signin" ? "Sign in" : "Create an account"}
      </h1>
      <p className="mt-2 text-center text-sm text-muted-foreground">
        Analyses are saved to your account so you can compare drafts.
      </p>

      <Card className="mt-6">
        <CardBody className="space-y-4">
          <div
            className="grid grid-cols-2 gap-1 rounded-lg bg-surface-muted p-1"
            role="tablist"
          >
            {(["signin", "signup"] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={mode === value}
                onClick={() => {
                  setMode(value);
                  setError(null);
                  setNotice(null);
                }}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  mode === value
                    ? "bg-surface text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {value === "signin" ? "Sign in" : "Sign up"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm focus:outline-2 focus:outline-primary"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                autoComplete={
                  mode === "signin" ? "current-password" : "new-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm focus:outline-2 focus:outline-primary"
              />
              {mode === "signup" && (
                <p className="mt-1 text-xs text-muted-foreground">
                  At least 6 characters.
                </p>
              )}
            </div>

            {error && (
              <div
                role="alert"
                className="flex gap-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:bg-rose-950/50 dark:text-rose-300"
              >
                <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                <span>{error}</span>
              </div>
            )}

            {notice && (
              <p className="rounded-lg bg-surface-muted px-3 py-2 text-sm text-muted-foreground">
                {notice}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={pending}>
              {pending && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {mode === "signin" ? "Sign in" : "Create account"}
            </Button>
          </form>

          {googleEnabled && (
            <>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="h-px flex-1 bg-border" />
                or
                <span className="h-px flex-1 bg-border" />
              </div>

              <Button variant="outline" className="w-full" onClick={handleGoogle}>
                Continue with Google
              </Button>
            </>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  // useSearchParams needs a Suspense boundary to keep the route statically renderable.
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
