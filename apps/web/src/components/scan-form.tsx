"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { createPublicScan } from "@agentworthy/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ScanForm() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError("");

    try {
      const result = await createPublicScan(url.trim());
      router.push(`/report/${result.scan_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start scan");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-xl mx-auto">
      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          type="text"
          placeholder="https://yourwebsite.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
          className="flex-1"
        />
        <Button type="submit" size="lg" disabled={loading || !url.trim()}>
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <>
              Scan Now
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
      {error && <p className="text-red-500 text-sm mt-2 text-center">{error}</p>}
    </form>
  );
}
