import Link from "next/link";
import { ScanForm } from "@/components/scan-form";
import { ThemeToggle } from "@/components/theme-provider";
import { Bot, Search, Code, Shield } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-accent" />
            <span className="font-semibold text-lg">Agentworthy</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground">
              Sign in
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="container mx-auto px-4 py-24 text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            Can AI agents do business
            <br />
            <span className="text-accent">with your website?</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-4 max-w-2xl mx-auto">
            Find out in 60 seconds.
          </p>
          <p className="text-muted-foreground mb-12 max-w-xl mx-auto">
            Audit your site for ChatGPT Operator, Claude computer use, and Perplexity
            shopping agent compatibility. Get your Transactability Score and actionable fixes.
          </p>

          <ScanForm />

          <p className="text-xs text-muted-foreground mt-4">
            Free scan. No signup required. 3 scans per day.
          </p>
        </section>

        <section className="border-t border-border bg-muted/30 py-20">
          <div className="container mx-auto px-4">
            <h2 className="text-2xl font-semibold text-center mb-12">
              What we check
            </h2>
            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              <FeatureCard
                icon={Search}
                title="Discoverability"
                description="Can AI agents find and access your site? robots.txt, llms.txt, sitemaps, and canonical tags."
              />
              <FeatureCard
                icon={Code}
                title="Machine Readability"
                description="Is your content readable without JavaScript? Structured data, SSR content, and machine-readable pricing."
              />
              <FeatureCard
                icon={Shield}
                title="Actionability"
                description="Can agents complete tasks? Semantic forms, accessible CTAs, and reachable checkout flows."
              />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-8 text-center text-sm text-muted-foreground">
        <p>Agentworthy — AI agent readiness auditing</p>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="text-center p-6">
      <Icon className="h-10 w-10 text-accent mx-auto mb-4" />
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
