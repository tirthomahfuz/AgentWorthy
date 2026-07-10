/**
 * Refuse to start in production without RESEND_API_KEY (magic links must not write to disk).
 */
export function assertProductionEmailConfig(): void {
  if (process.env.NODE_ENV === "production" && !process.env.RESEND_API_KEY) {
    throw new Error(
      "RESEND_API_KEY is required when NODE_ENV=production. " +
        "Email magic links cannot be sent without a mail provider."
    );
  }
}
