import { execSync } from "child_process";

const TEST_EMAIL = "e2e-test@agentworthy.example";

export default async function globalSetup() {
  const dbUrl = process.env.DATABASE_URL || "postgresql://agentworthy@localhost:5432/agentworthy";
  const sql = `
    DELETE FROM checks WHERE scan_id IN (
      SELECT id FROM scans WHERE site_id IN (
        SELECT id FROM sites WHERE user_id IN (SELECT id FROM users WHERE email = '${TEST_EMAIL}')
      )
    );
    DELETE FROM llm_usage WHERE scan_id IN (
      SELECT id FROM scans WHERE site_id IN (
        SELECT id FROM sites WHERE user_id IN (SELECT id FROM users WHERE email = '${TEST_EMAIL}')
      )
    );
    DELETE FROM scans WHERE site_id IN (
      SELECT id FROM sites WHERE user_id IN (SELECT id FROM users WHERE email = '${TEST_EMAIL}')
    );
    DELETE FROM sites WHERE user_id IN (SELECT id FROM users WHERE email = '${TEST_EMAIL}');
  `;
  try {
    execSync(`psql "${dbUrl}" -c "${sql.replace(/\n/g, " ")}"`, { stdio: "pipe" });
  } catch {
    // DB may be unavailable in CI until compose is up; per-test cleanup handles retries
  }
}
