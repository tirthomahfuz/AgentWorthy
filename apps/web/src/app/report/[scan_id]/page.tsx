"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Bot, Loader2, ExternalLink } from "lucide-react";
import { getScanReport, type ScanReport } from "@agentworthy/shared";
import { ThemeToggle } from "@/components/theme-provider";
import { ScoreGauge } from "@/components/score-gauge";
import { CheckRow, CategoryBreakdown } from "@/components/check-row";
import { Button } from "@/components/ui/button";

const POLL_INTERVAL = 2000;

export default function ReportPage({ params }: { params: { scan_id: string } }) {
  const [report, setReport] = useState<ScanReport | null>(null);
  const [error, setError] = useState("");
  const scanId = params.scan_id;

  const fetchReport = useCallback(async () => {
    try {
      const data = await getScanReport(scanId);
      setReport(data);
      return data;
    } catch {
      setError("Scan not found");
      return null;
    }
  }, [scanId]);

  useEffect(() => {
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
  }, [fetchReport]);

  const isLoading = !report || (report.status !== "complete" && report.status !== "failed");
  const implementedChecks = report?.checks.filter((c) => c.status !== "not_applicable") || [];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-accent" />
            <span className="font-semibold text-lg">Agentworthy</span>
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-12">
        {error ? (
          <div className="text-center py-20">
            <p className="text-red-500 mb-4">{error}</p>
            <Link href="/">
              <Button>Start a new scan</Button>
            </Link>
          </div>
        ) : isLoading ? (
          <div className="text-center py-20">
            <Loader2 className="h-12 w-12 animate-spin text-accent mx-auto mb-4" />
            <h2 className="text-2xl font-semibold mb-2">Scanning your site...</h2>
            <p className="text-muted-foreground mb-2">
              {report?.url && (
                <span className="inline-flex items-center gap-1">
                  <ExternalLink className="h-4 w-4" />
                  {report.url}
                </span>
              )}
            </p>
            <p className="text-sm text-muted-foreground capitalize">
              Status: {report?.status || "starting"}
            </p>

            {implementedChecks.length > 0 && (
              <div className="mt-8 max-w-2xl mx-auto text-left space-y-2">
                <p className="text-sm font-medium text-muted-foreground mb-3">Checks completed:</p>
                {implementedChecks.map((check) => (
                  <CheckRow key={check.id} check={check} blurFix />
                ))}
              </div>
            )}
          </div>
        ) : report?.status === "failed" ? (
          <div className="text-center py-20">
            <p className="text-red-500 mb-2">Scan failed</p>
            <p className="text-muted-foreground mb-4">{report.error_message}</p>
            <Link href="/">
              <Button>Try again</Button>
            </Link>
          </div>
        ) : report ? (
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-8">
              <p className="text-muted-foreground mb-1">Transactability Report</p>
              <h1 className="text-2xl font-semibold mb-1">{report.url}</h1>
              <p className="text-sm text-muted-foreground font-mono">Scan ID: {report.id}</p>
            </div>

            <div className="flex flex-col items-center mb-12">
              <ScoreGauge
                score={report.overall_score ?? 0}
                grade={report.letter_grade ?? "F"}
              />
              <p className="text-muted-foreground mt-4 text-center max-w-md">
                Your Transactability Score measures how well AI agents can find, understand,
                and transact with your website.
              </p>
            </div>

            <div className="mb-12 p-6 border border-border rounded-xl">
              <h2 className="font-semibold mb-4">Category Breakdown</h2>
              <CategoryBreakdown checks={report.checks} />
            </div>

            <div className="space-y-3 mb-12">
              <h2 className="font-semibold">All Checks</h2>
              {report.checks
                .filter((c) => c.status !== "not_applicable")
                .map((check) => (
                  <CheckRow key={check.id} check={check} blurFix />
                ))}
            </div>

            <div className="text-center p-8 border border-accent/30 rounded-xl bg-accent/5">
              <h3 className="text-xl font-semibold mb-2">Want the fixes?</h3>
              <p className="text-muted-foreground mb-4">
                Upgrade to see copy-paste fix code for every failed check — JSON-LD,
                HTML snippets, and llms.txt files ready to deploy.
              </p>
              <Button size="lg" disabled>
                Upgrade — Coming in Phase 5
              </Button>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
