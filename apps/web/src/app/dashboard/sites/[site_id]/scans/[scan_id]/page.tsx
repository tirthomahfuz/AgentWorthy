"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { getSiteScanReport, type ScanReport } from "@agentworthy/shared";
import { ScoreGauge } from "@/components/score-gauge";
import { CheckRow, CategoryBreakdown } from "@/components/check-row";

const POLL_INTERVAL = 2000;

export default function AuthenticatedScanPage() {
  const { site_id, scan_id } = useParams<{ site_id: string; scan_id: string }>();
  const { status } = useSession();
  const router = useRouter();
  const { accessToken } = useAuth();
  const [report, setReport] = useState<ScanReport | null>(null);

  const fetchReport = useCallback(async () => {
    if (!accessToken) return null;
    const data = await getSiteScanReport(accessToken, site_id, scan_id);
    setReport(data);
    return data;
  }, [accessToken, site_id, scan_id]);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  useEffect(() => {
    if (!accessToken) return;
    let interval: NodeJS.Timeout;
    const poll = async () => {
      const data = await fetchReport();
      if (data && (data.status === "complete" || data.status === "failed")) {
        clearInterval(interval);
      }
    };
    poll();
    interval = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchReport, accessToken]);

  const isLoading = !report || (report.status !== "complete" && report.status !== "failed");

  return (
    <div className="min-h-screen container mx-auto px-4 py-8 max-w-3xl">
      <Link href="/dashboard" className="text-sm text-accent hover:underline mb-4 inline-block">
        ← Dashboard
      </Link>

      {isLoading ? (
        <div className="text-center py-20">
          <Loader2 className="h-12 w-12 animate-spin text-accent mx-auto mb-4" />
          <p>Scanning {report?.url}...</p>
          <p className="text-sm text-muted-foreground capitalize">Status: {report?.status || "starting"}</p>
        </div>
      ) : report ? (
        <>
          <div className="text-center mb-8">
            <h1 className="text-2xl font-semibold">{report.url}</h1>
            <p className="text-sm text-muted-foreground">Authenticated report — fixes shown unblurred</p>
          </div>
          <div className="flex justify-center mb-8">
            <ScoreGauge score={report.overall_score ?? 0} grade={report.letter_grade ?? "F"} />
          </div>
          <CategoryBreakdown checks={report.checks} />
          <div className="mt-8 space-y-3">
            {report.checks
              .filter((c) => c.status !== "not_applicable")
              .map((check) => (
                <CheckRow key={check.id} check={check} blurFix={false} />
              ))}
          </div>
          <div className="mt-8 p-4 border border-dashed border-border rounded-lg text-sm text-muted-foreground">
            Fix code generation arrives in Stage 4. Placeholder fix blocks render unblurred for paid users.
          </div>
        </>
      ) : null}
    </div>
  );
}
