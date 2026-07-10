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
  authenticated?: boolean;
}

export interface PublicScanResponse {
  scan_id: string;
  public_scan_id: string;
  status: string;
}

export interface Site {
  id: string;
  root_url: string;
  display_name: string | null;
  verified: boolean;
  verification_token: string | null;
  created_at: string;
  latest_score: number | null;
  latest_grade: string | null;
  last_scan_at: string | null;
}

export interface AuthSyncResponse {
  user_id: string;
  email: string;
  name: string | null;
  access_token: string;
}

/** Browser uses same-origin proxy on Vercel; server/SSR uses API_URL directly. */
export function getApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") return "/api/backend";
  return process.env.API_URL || "http://localhost:8000";
}

/** @deprecated use getApiUrl() — kept for backwards compatibility */
export const API_URL = typeof window !== "undefined" ? "/api/backend" : (process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000");

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${getApiUrl()}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function createPublicScan(url: string, email?: string): Promise<PublicScanResponse> {
  return apiFetch("/public/scan", {
    method: "POST",
    body: JSON.stringify({ url, email }),
  });
}

export async function getScanReport(scanId: string, token?: string): Promise<ScanReport> {
  if (token) {
    // Authenticated scans use site-scoped route — caller provides full path
    return apiFetch(`/sites/scan-placeholder/scans/${scanId}`, {}, token);
  }
  return apiFetch(`/public/scan/${scanId}`);
}

export async function syncUser(email: string, name?: string): Promise<AuthSyncResponse> {
  return apiFetch("/auth/sync", {
    method: "POST",
    body: JSON.stringify({ email, name }),
  });
}

export async function listSites(token: string): Promise<Site[]> {
  return apiFetch("/sites", {}, token);
}

export async function createSite(
  token: string,
  rootUrl: string,
  displayName: string
): Promise<Site> {
  return apiFetch(
    "/sites",
    { method: "POST", body: JSON.stringify({ root_url: rootUrl, display_name: displayName }) },
    token
  );
}

export async function verifySite(
  token: string,
  siteId: string
): Promise<{ verified: boolean; message: string }> {
  return apiFetch(`/sites/${siteId}/verify`, { method: "POST" }, token);
}

export async function triggerScan(
  token: string,
  siteId: string
): Promise<{ scan_id: string; status: string }> {
  return apiFetch(`/sites/${siteId}/scans`, { method: "POST" }, token);
}

export async function getSiteSparkline(
  token: string,
  siteId: string
): Promise<{ date: string | null; score: number }[]> {
  return apiFetch(`/sites/${siteId}/sparkline`, {}, token);
}

export async function getSiteScanReport(
  token: string,
  siteId: string,
  scanId: string
): Promise<ScanReport> {
  return apiFetch(`/sites/${siteId}/scans/${scanId}`, {}, token);
}

export async function getVerificationInstructions(
  token: string,
  siteId: string
): Promise<{ meta_tag: string; dns_txt_host: string; dns_txt_value: string }> {
  return apiFetch(`/sites/${siteId}/verification-instructions`, {}, token);
}
