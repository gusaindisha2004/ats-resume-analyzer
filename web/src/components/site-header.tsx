import Link from "next/link";
import { ScanLine } from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { SignOutButton } from "@/components/sign-out-button";

export async function SiteHeader() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-5xl items-center gap-6 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <ScanLine className="size-5 text-primary" aria-hidden />
          <span>ATS Analyzer</span>
        </Link>

        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/analyze"
            className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground"
          >
            Analyze
          </Link>
          {user && (
            <Link
              href="/history"
              className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground"
            >
              History
            </Link>
          )}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          {user ? (
            <>
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {user.email}
              </span>
              <SignOutButton />
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
