import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import EmailProvider from "next-auth/providers/email";
import { createDevAuthAdapter } from "@/lib/auth-adapter";

const resendKey = process.env.RESEND_API_KEY;

export const authOptions: NextAuthOptions = {
  adapter: createDevAuthAdapter(),
  session: { strategy: "jwt", maxAge: 30 * 24 * 60 * 60 },
  pages: {
    signIn: "/login",
    verifyRequest: "/login/verify",
  },
  providers: [
    EmailProvider({
      server: { host: "localhost", port: 1025, auth: { user: "", pass: "" } },
      from: process.env.EMAIL_FROM || "Agentworthy <onboarding@agentworthy.dev>",
      async sendVerificationRequest({ identifier, url }) {
        if (!resendKey) {
          if (process.env.NODE_ENV === "production") {
            const { assertProductionEmailConfig } = await import("@/lib/auth-guard");
            assertProductionEmailConfig();
          }
          console.log("\n[Agentworthy Dev Auth] Magic link for", identifier);
          console.log(url, "\n");
          try {
            const fs = await import("fs");
            fs.writeFileSync("/tmp/agentworthy-magic-link.txt", url);
          } catch {
            // ignore in edge runtime
          }
          return;
        }
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${resendKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: process.env.EMAIL_FROM || "Agentworthy <onboarding@agentworthy.dev>",
            to: identifier,
            subject: "Sign in to Agentworthy",
            html: `<p><a href="${url}">Sign in to Agentworthy</a></p>`,
          }),
        });
      },
    }),
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? [
          GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
          }),
        ]
      : []),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user?.email) {
        token.email = user.email;
        token.name = user.name;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user && token.email) {
        session.user.email = token.email as string;
        session.user.name = token.name as string | undefined;
      }
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET || "dev-nextauth-secret-change-me",
};
