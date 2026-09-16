"use client"; // Error boundaries must be Client Components

/**
 * Last-resort boundary for errors thrown in the root layout itself, where
 * `error.tsx` cannot reach.
 *
 * This replaces the root layout when active, so it must render its own <html>
 * and <body>. It also does not receive globals.css, which is why the styling
 * here is inline rather than using theme tokens — and why it deliberately
 * follows the OS colour scheme instead of the app's.
 */
export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en">
      <head>
        <title>Something went wrong</title>
      </head>
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          fontFamily:
            "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          colorScheme: "light dark",
          padding: "1.5rem",
        }}
      >
        <main style={{ maxWidth: "26rem", textAlign: "center" }}>
          <h1 style={{ fontSize: "1.125rem", margin: "0 0 0.5rem" }}>
            Something went wrong
          </h1>
          <p style={{ fontSize: "0.875rem", opacity: 0.7, margin: "0 0 1.25rem" }}>
            The application failed to start. Trying again may resolve it.
          </p>
          {error.digest && (
            <p
              style={{
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                fontSize: "0.75rem",
                opacity: 0.6,
                margin: "0 0 1.25rem",
              }}
            >
              Reference: {error.digest}
            </p>
          )}
          <button
            onClick={() => retry()}
            style={{
              background: "#0049DE",
              color: "#fff",
              border: 0,
              borderRadius: "0.5rem",
              padding: "0.625rem 1.25rem",
              fontSize: "0.875rem",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
