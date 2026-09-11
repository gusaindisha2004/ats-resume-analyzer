import type { Metadata } from "next";
import Link from "next/link";
import { TriangleAlert } from "lucide-react";
import { getHistoryServer } from "@/lib/api-server";
import { Card, CardBody } from "@/components/ui/card";
import { HistoryList } from "@/app/history/history-list";

export const metadata: Metadata = { title: "History" };

// Every visit should show the latest saved analyses.
export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const { data, error } = await getHistoryServer();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">History</h1>
        <p className="mt-2 text-muted-foreground">
          Every analysis saved to your account. Useful for checking a rewrite
          actually moved the number.
        </p>
      </div>

      {error ? (
        <Card>
          <CardBody className="flex items-start gap-2.5 text-sm">
            <TriangleAlert
              className="mt-0.5 size-4 shrink-0 text-rose-500"
              aria-hidden
            />
            <p>{error}</p>
          </CardBody>
        </Card>
      ) : data && data.length === 0 ? (
        <Card>
          <CardBody className="py-12 text-center">
            <p className="text-sm text-muted-foreground">Nothing saved yet.</p>
            <Link
              href="/analyze"
              className="mt-4 inline-block rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-hover"
            >
              Analyze a resume
            </Link>
          </CardBody>
        </Card>
      ) : (
        <HistoryList entries={data ?? []} />
      )}
    </div>
  );
}
