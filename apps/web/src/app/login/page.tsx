"use client";

import { useState } from "react";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const { signInEmail } = useAuth();

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    await signInEmail(email);
    setSent(true);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <Link href="/" className="flex items-center gap-2 mb-8">
        <Bot className="h-8 w-8 text-accent" />
        <span className="text-xl font-semibold">Agentworthy</span>
      </Link>
      <div className="w-full max-w-md border border-border rounded-xl p-8">
        <h1 className="text-2xl font-semibold mb-2">Sign in</h1>
        <p className="text-muted-foreground text-sm mb-6">
          Manage your sites and run full audits with fix recommendations.
        </p>
        {sent ? (
          <p className="text-sm text-center py-4">
            Check your email for a magic link. In dev mode, the link is printed to the server console.
          </p>
        ) : (
          <form onSubmit={handleEmail} className="space-y-4">
            <Input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Button type="submit" className="w-full" size="lg">
              Send magic link
            </Button>
          </form>
        )}
        {process.env.NEXT_PUBLIC_GOOGLE_ENABLED === "true" && (
          <Button
            variant="outline"
            className="w-full mt-4"
            onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
          >
            Continue with Google
          </Button>
        )}
      </div>
    </div>
  );
}
