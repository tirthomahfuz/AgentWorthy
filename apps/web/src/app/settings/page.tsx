"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Bot } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { status, data: session } = useSession();
  const router = useRouter();
  const { sites, signOutUser } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  return (
    <div className="min-h-screen container mx-auto px-4 py-8 max-w-2xl">
      <Link href="/dashboard" className="text-sm text-accent hover:underline mb-6 inline-block">
        ← Dashboard
      </Link>
      <h1 className="text-2xl font-semibold mb-8">Settings</h1>

      <section className="border border-border rounded-xl p-6 mb-6">
        <h2 className="font-medium mb-4">Profile</h2>
        <p className="text-sm"><span className="text-muted-foreground">Email:</span> {session?.user?.email}</p>
        <p className="text-sm mt-1"><span className="text-muted-foreground">Name:</span> {session?.user?.name || "—"}</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={signOutUser}>
          Sign out
        </Button>
      </section>

      <section className="border border-border rounded-xl p-6 mb-6">
        <h2 className="font-medium mb-4">Connected sites</h2>
        {sites.length === 0 ? (
          <p className="text-sm text-muted-foreground">No sites connected.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {sites.map((s) => (
              <li key={s.id} className="flex justify-between">
                <span>{s.display_name}</span>
                <span className="text-muted-foreground">{s.verified ? "Verified" : "Unverified"}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="border border-border rounded-xl p-6 opacity-60">
        <h2 className="font-medium mb-2">Billing</h2>
        <p className="text-sm text-muted-foreground">
          Stripe billing arrives in Stage 5. You are on the free plan.
        </p>
      </section>
    </div>
  );
}
