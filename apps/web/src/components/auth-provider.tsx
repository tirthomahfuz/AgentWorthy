"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useSession, signOut } from "next-auth/react";
import {
  API_URL,
  syncUser,
  type Site,
  listSites,
  createSite as apiCreateSite,
  verifySite,
  triggerScan,
  getSiteSparkline,
} from "@agentworthy/shared";

interface AuthContextValue {
  accessToken: string | null;
  sites: Site[];
  loading: boolean;
  refreshSites: () => Promise<void>;
  addSite: (rootUrl: string, displayName: string) => Promise<Site>;
  verifySiteNow: (siteId: string) => Promise<void>;
  scanSite: (siteId: string) => Promise<string>;
  getSparkline: (siteId: string) => Promise<{ date: string | null; score: number }[]>;
  signInEmail: (email: string) => Promise<void>;
  signOutUser: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function sync() {
      if (status !== "authenticated" || !session?.user?.email) {
        setAccessToken(null);
        setSites([]);
        setLoading(false);
        return;
      }
      try {
        const res = await syncUser(session.user.email, session.user.name || undefined);
        setAccessToken(res.access_token);
        const siteList = await listSites(res.access_token);
        setSites(siteList);
      } catch (e) {
        console.error("Auth sync failed", e);
      } finally {
        setLoading(false);
      }
    }
    sync();
  }, [session, status]);

  const refreshSites = useCallback(async () => {
    if (!accessToken) return;
    setSites(await listSites(accessToken));
  }, [accessToken]);

  const value: AuthContextValue = {
    accessToken,
    sites,
    loading,
    refreshSites,
    addSite: async (rootUrl, displayName) => {
      if (!accessToken) throw new Error("Not authenticated");
      const site = await apiCreateSite(accessToken, rootUrl, displayName);
      await refreshSites();
      return site;
    },
    verifySiteNow: async (siteId) => {
      if (!accessToken) throw new Error("Not authenticated");
      await verifySite(accessToken, siteId);
      await refreshSites();
    },
    scanSite: async (siteId) => {
      if (!accessToken) throw new Error("Not authenticated");
      const res = await triggerScan(accessToken, siteId);
      return res.scan_id;
    },
    getSparkline: async (siteId) => {
      if (!accessToken) return [];
      return getSiteSparkline(accessToken, siteId);
    },
    signInEmail: async (email) => {
      const csrfRes = await fetch("/api/auth/csrf");
      const { csrfToken } = await csrfRes.json();
      await fetch("/api/auth/signin/email", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          email,
          csrfToken,
          callbackUrl: "/dashboard",
          json: "true",
        }),
      });
    },
    signOutUser: () => signOut({ callbackUrl: "/" }),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
