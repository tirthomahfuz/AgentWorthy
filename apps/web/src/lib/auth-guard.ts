/**
 * Refuse to start in production without RESEND_API_KEY (magic links must not write to disk).
 */
export function assertProductionEmailConfig(): void {
  // Next.js sets NODE_ENV=production during `next build`; only enforce at runtime.
  if (process.env.NEXT_PHASE === "phase-production-build") return;
  if (process.env.NODE_ENV === "production" && !process.env.RESEND_API_KEY) {
    throw new Error(
      "RESEND_API_KEY is required when NODE_ENV=production. " +
        "Email magic links cannot be sent without a mail provider."
    );
  }
}
