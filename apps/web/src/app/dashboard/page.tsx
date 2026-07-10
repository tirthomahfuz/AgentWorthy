"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Bot, Plus, Settings, LogOut, Globe, ShieldCheck, ShieldX } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { useAuth } from "@/components/auth-provider";
import { ThemeToggle } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Site } from "@agentworthy/shared";

export default function DashboardPage() {
  const { status } = useSession();
  const router = useRouter();
  const { sites, loading, accessToken, addSite, verifySiteNow, scanSite, getSparkline, signOutUser, refreshSites } =
    useAuth();
  const [showAdd, setShowAdd] = useState(false);
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [scanning, setScanning] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await addSite(url, name);
    setUrl("");
    setName("");
    setShowAdd(false);
  };

  const handleScan = async (siteId: string) => {
    setScanning(siteId);
    try {
      const scanId = await scanSite(siteId);
      router.push(`/dashboard/sites/${siteId}/scans/${scanId}`);
    } finally {
      setScanning(null);
    }
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground">
        Loading dashboard...
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-accent" />
            <span className="font-semibold">Agentworthy</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/settings">
              <Button variant="ghost" size="sm">
                <Settings className="h-4 w-4 mr-1" /> Settings
              </Button>
            </Link>
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={signOutUser}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold">Your sites</h1>
            <p className="text-muted-foreground text-sm">Monitor AI agent readiness across your properties</p>
          </div>
          <Button onClick={() => setShowAdd(true)}>
            <Plus className="h-4 w-4 mr-1" /> Add site
          </Button>
        </div>

        {showAdd && (
          <form onSubmit={handleAdd} className="mb-8 p-6 border border-border rounded-xl space-y-3 max-w-lg">
            <Input placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} required />
            <Input placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} required />
            <div className="flex gap-2">
              <Button type="submit">Add site</Button>
              <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>
                Cancel
              </Button>
            </div>
          </form>
        )}

        {sites.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-border rounded-xl">
            <Globe className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h2 className="text-lg font-medium mb-2">No sites yet</h2>
            <p className="text-muted-foreground text-sm mb-4 max-w-sm mx-auto">
              Add your first website to start auditing AI agent readiness. Verify ownership to unlock 200-page scans.
            </p>
            <Button onClick={() => setShowAdd(true)}>
              <Plus className="h-4 w-4 mr-1" /> Add your first site
            </Button>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {sites.map((site) => (
              <SiteCard
                key={site.id}
                site={site}
                onScan={() => handleScan(site.id)}
                onVerify={() => verifySiteNow(site.id)}
                scanning={scanning === site.id}
                getSparkline={getSparkline}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function SiteCard({
  site,
  onScan,
  onVerify,
  scanning,
  getSparkline,
}: {
  site: Site;
  onScan: () => void;
  onVerify: () => void;
  scanning: boolean;
  getSparkline: (id: string) => Promise<{ date: string | null; score: number }[]>;
}) {
  const [sparkline, setSparkline] = useState<{ date: string; score: number }[]>([]);

  useEffect(() => {
    getSparkline(site.id).then((data) =>
      setSparkline(
        data
          .filter((d) => d.date && d.score != null)
          .map((d) => ({ date: d.date!.slice(0, 10), score: d.score }))
      )
    );
  }, [site.id, site.latest_score, getSparkline]);

  return (
    <div className="border border-border rounded-xl p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold">{site.display_name}</h3>
          <p className="text-sm text-muted-foreground truncate max-w-xs">{site.root_url}</p>
        </div>
        {site.verified ? (
          <ShieldCheck className="h-5 w-5 text-green-500 shrink-0" aria-label="Verified" />
        ) : (
          <ShieldX className="h-5 w-5 text-yellow-500 shrink-0" aria-label="Unverified" />
        )}
      </div>

      <div className="flex items-end gap-4 mb-4">
        <div>
          <span className="font-mono text-3xl font-bold">{site.latest_score ?? "—"}</span>
          {site.latest_grade && (
            <span className="ml-2 font-mono text-lg text-muted-foreground">{site.latest_grade}</span>
          )}
        </div>
        {sparkline.length > 0 && (
          <div className="flex-1 h-16">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparkline}>
                <XAxis dataKey="date" hide />
                <YAxis domain={[0, 100]} hide />
                <Tooltip />
                <Line type="monotone" dataKey="score" stroke="#2563EB" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <p className="text-xs text-muted-foreground mb-4">
        {site.last_scan_at
          ? `Last scan: ${new Date(site.last_scan_at).toLocaleString()}`
          : "No scans yet — run your first audit"}
      </p>

      <div className="flex gap-2">
        <Button size="sm" onClick={onScan} disabled={scanning}>
          {scanning ? "Starting..." : "Scan now"}
        </Button>
        {!site.verified && (
          <Button size="sm" variant="outline" onClick={onVerify}>
            Verify ownership
          </Button>
        )}
        <Link href={`/dashboard/sites/${site.id}`}>
          <Button size="sm" variant="ghost">
            Details
          </Button>
        </Link>
      </div>
    </div>
  );
}
