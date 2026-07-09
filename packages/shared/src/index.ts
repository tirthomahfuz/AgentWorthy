export type CheckStatus = "pass" | "warn" | "fail" | "not_applicable";

export type CheckCategory =
  | "discoverability"
  | "machine_readability"
  | "actionability"
  | "trust_freshness"
  | "performance";

export interface CheckResult {
  id: string;
  category: CheckCategory;
  check_key: string;
  status: CheckStatus;
  weight: number;
  evidence: Record<string, unknown> | null;
  plain_explanation: string | null;
  fix_code: string | null;
  fix_language: string | null;
}

export interface ScanReport {
  id: string;
  status: string;
  overall_score: number | null;
  letter_grade: string | null;
  site_type: string | null;
  url: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  checks: CheckResult[];
}

export interface PublicScanResponse {
  scan_id: string;
  public_scan_id: string;
  status: string;
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function createPublicScan(url: string, email?: string): Promise<PublicScanResponse> {
  const res = await fetch(`${API_URL}/public/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Scan failed" }));
    throw new Error(err.detail || "Scan failed");
  }
  return res.json();
}

export async function getScanReport(scanId: string): Promise<ScanReport> {
  const res = await fetch(`${API_URL}/public/scan/${scanId}`);
  if (!res.ok) {
    throw new Error("Scan not found");
  }
  return res.json();
}
