import Link from "next/link";
import { Card, CardBody } from "@/components/ui/card";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-lg py-16">
      <Card>
        <CardBody className="space-y-4 text-center">
          <p className="font-mono text-3xl font-semibold text-primary">404</p>
          <div>
            <h1 className="text-lg font-semibold">Page not found</h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              That URL doesn&apos;t exist.
            </p>
          </div>
          <div className="flex justify-center gap-3 pt-1">
            <Link
              href="/"
              className="rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
            >
              Go home
            </Link>
            <Link
              href="/analyze"
              className="rounded-lg border border-border bg-surface px-5 py-2 text-sm font-medium transition-colors hover:border-primary/30 hover:bg-primary-subtle"
            >
              Analyze a resume
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
