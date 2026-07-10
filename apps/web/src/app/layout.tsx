import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agentworthy — AI Agent Readiness Audit",
  description:
    "Can AI agents do business with your website? Find out in 60 seconds. Audit your site for ChatGPT, Claude, and Perplexity agent compatibility.",
  openGraph: {
    title: "Agentworthy — AI Agent Readiness Audit",
    description: "Can AI agents do business with your website? Find out in 60 seconds.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <ThemeProvider>{children}</ThemeProvider>
        </Providers>
      </body>
    </html>
  );
}
