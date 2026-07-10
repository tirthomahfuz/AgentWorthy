#!/usr/bin/env node
/** Unit test for production email guard (A5). Run: node apps/web/src/lib/auth-guard.test.mjs */

import assert from "node:assert/strict";
import { assertProductionEmailConfig } from "./auth-guard.ts";

const origNodeEnv = process.env.NODE_ENV;
const origResend = process.env.RESEND_API_KEY;

function restore() {
  process.env.NODE_ENV = origNodeEnv;
  if (origResend === undefined) delete process.env.RESEND_API_KEY;
  else process.env.RESEND_API_KEY = origResend;
}

try {
  process.env.NODE_ENV = "production";
  delete process.env.RESEND_API_KEY;
  assert.throws(() => assertProductionEmailConfig(), /RESEND_API_KEY is required/);

  process.env.RESEND_API_KEY = "re_test_key";
  assert.doesNotThrow(() => assertProductionEmailConfig());

  process.env.NODE_ENV = "development";
  delete process.env.RESEND_API_KEY;
  assert.doesNotThrow(() => assertProductionEmailConfig());

  console.log("auth-guard tests passed");
} finally {
  restore();
}
