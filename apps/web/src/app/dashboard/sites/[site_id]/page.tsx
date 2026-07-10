"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { getVerificationInstructions } from "@agentworthy/shared";

export default function SiteDetailPage() {
  const { site_id } = useParams<{ site_id: string }>();
  const { status } = useSession();
  const router = useRouter();
  const { sites, accessToken, verifySiteNow } = useAuth();
  const [instructions, setInstructions] = useState<{
    meta_tag: string;
    dns_txt_host: string;
    dns_txt_value: string;
  } | null>(null);

  const site = sites.find((s) => s.id === site_id);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  useEffect(() => {
    if (accessToken && site_id && site && !site.verified) {
      getVerificationInstructions(accessToken, site_id).then(setInstructions);
    }
  }, [accessToken, site_id, site]);

  if (!site) {
    return <div className="p-8">Site not found</div>;
  }

  return (
    <div className="min-h-screen container mx-auto px-4 py-8 max-w-2xl">
      <Link href="/dashboard" className="inline-flex items-center text-sm text-muted-foreground mb-6 hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Back to dashboard
      </Link>
      <h1 className="text-2xl font-semibold mb-1">{site.display_name}</h1>
      <p className="text-muted-foreground mb-6">{site.root_url}</p>

      <div className="border border-border rounded-xl p-6 mb-6">
        <h2 className="font-medium mb-2">Verification status</h2>
        <p className="text-sm text-muted-foreground mb-4">
          {site.verified
            ? "This site is verified. Scans crawl up to 200 pages."
            : "Unverified sites are limited to 25 pages per scan."}
        </p>
        {!site.verified && instructions && (
          <div className="space-y-4 text-sm">
            <div>
              <p className="font-medium mb-1">Option 1: Meta tag</p>
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto text-xs">{instructions.meta_tag}</pre>
            </div>
            <div>
              <p className="font-medium mb-1">Option 2: DNS TXT record</p>
              <p>Host: {instructions.dns_txt_host}</p>
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto text-xs mt-1">
                {instructions.dns_txt_value}
              </pre>
            </div>
            <Button onClick={() => verifySiteNow(site.id)}>Verify now</Button>
          </div>
        )}
      </div>
    </div>
  );
}
