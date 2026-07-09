"use client";

import { useState } from "react";
import { CheckCircle2, AlertTriangle, XCircle, MinusCircle, ChevronDown, Copy, Check } from "lucide-react";
import type { CheckResult } from "@agentworthy/shared";
import { cn } from "@/lib/utils";

const STATUS_ICONS = {
  pass: CheckCircle2,
  warn: AlertTriangle,
  fail: XCircle,
  not_applicable: MinusCircle,
};

const STATUS_COLORS = {
  pass: "text-green-500",
  warn: "text-yellow-500",
  fail: "text-red-500",
  not_applicable: "text-muted-foreground",
};

const CATEGORY_LABELS: Record<string, string> = {
  discoverability: "Discoverability",
  machine_readability: "Machine Readability",
  actionability: "Actionability",
  trust_freshness: "Trust & Freshness",
  performance: "Performance for Agents",
};

interface CheckRowProps {
  check: CheckResult;
  blurFix?: boolean;
}

export function CheckRow({ check, blurFix = false }: CheckRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const Icon = STATUS_ICONS[check.status] || MinusCircle;

  const copyFix = async () => {
    if (check.fix_code) {
      await navigator.clipboard.writeText(check.fix_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-muted/50 transition-colors"
      >
        <Icon className={cn("h-5 w-5 shrink-0", STATUS_COLORS[check.status])} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{formatCheckKey(check.check_key)}</p>
          <p className="text-sm text-muted-foreground truncate">{check.plain_explanation}</p>
        </div>
        <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", expanded && "rotate-180")} />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
          <p className="text-sm">{check.plain_explanation}</p>

          {check.evidence && Object.keys(check.evidence).length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Evidence</p>
              <pre className="text-xs bg-muted p-3 rounded-lg overflow-x-auto font-mono">
                {JSON.stringify(check.evidence, null, 2)}
              </pre>
            </div>
          )}

          {check.fix_code && (
            <div className={cn("relative", blurFix && "select-none")}>
              {blurFix && (
                <div className="absolute inset-0 backdrop-blur-sm bg-background/60 z-10 flex items-center justify-center rounded-lg">
                  <p className="text-sm font-medium text-center px-4">
                    Upgrade to see the fix code
                  </p>
                </div>
              )}
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs font-medium text-muted-foreground">
                  Fix {check.fix_language && `(${check.fix_language})`}
                </p>
                {!blurFix && (
                  <button onClick={copyFix} className="text-xs flex items-center gap-1 text-accent hover:underline">
                    {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                )}
              </div>
              <pre className="text-xs bg-muted p-3 rounded-lg overflow-x-auto font-mono">
                {check.fix_code}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatCheckKey(key: string): string {
  return key.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

interface CategoryBreakdownProps {
  checks: CheckResult[];
}

export function CategoryBreakdown({ checks }: CategoryBreakdownProps) {
  const categories = Array.from(new Set(checks.map((c) => c.category)));

  return (
    <div className="space-y-4">
      {categories.map((cat) => {
        const catChecks = checks.filter((c) => c.category === cat && c.status !== "not_applicable");
        if (catChecks.length === 0) return null;

        const passCount = catChecks.filter((c) => c.status === "pass").length;
        const total = catChecks.length;
        const pct = Math.round((passCount / total) * 100);

        return (
          <div key={cat}>
            <div className="flex justify-between text-sm mb-1">
              <span>{CATEGORY_LABELS[cat] || cat}</span>
              <span className="font-mono text-muted-foreground">{pct}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
