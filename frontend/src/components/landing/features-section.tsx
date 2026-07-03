import {
  Coins,
  GitBranch,
  GitCommit,
  Network,
  Radio,
  Server,
  Sparkles,
  Users,
} from "lucide-react";

import { ProviderBadge } from "@/components/landing/provider-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CATEGORIES = [
  {
    title: "Workspace collaboration",
    icon: Users,
    features: [
      "Shared workspaces and invitations",
      "Conversation participants and ownership",
      "Live presence and typing indicators",
    ],
  },
  {
    title: "Ownership-first routing",
    icon: Sparkles,
    features: [
      "Routes through the sender's own providers first",
      "Multi-provider accounts per user",
      "Anthropic, OpenAI, Gemini, Groq, and Ollama",
    ],
    providers: ["OpenAI", "Anthropic", "Gemini", "Groq", "Ollama"] as const,
  },
  {
    title: "Borrowing engine",
    icon: Coins,
    features: [
      "Borrow providers from conversation participants",
      "Lending preferences and share limits",
      "Transparent borrowed execution metadata",
    ],
  },
  {
    title: "Conversation branching",
    icon: GitBranch,
    features: [
      "Branch from any message",
      "Independent branch ownership",
      "Lineage and read-only branch viewing",
    ],
  },
  {
    title: "Conversation commits",
    icon: GitCommit,
    features: [
      "Manual commits with Git-like hashes",
      "Automatic checkpoints after assistant replies",
      "Commit history and deep links",
    ],
  },
  {
    title: "Branch visualization",
    icon: Network,
    features: [
      "Branch manager and overview",
      "Commit graph across a conversation family",
      "Ahead / behind status metadata",
    ],
  },
  {
    title: "Realtime collaboration",
    icon: Radio,
    features: [
      "WebSocket streaming responses",
      "Live credit and routing events",
      "Instant message sync for participants",
    ],
  },
  {
    title: "Budget management",
    icon: Coins,
    features: [
      "Workspace budgets and credit ledger",
      "Borrow limits and lending preferences",
      "Routing policies and account ownership",
    ],
  },
  {
    title: "Provider management",
    icon: Server,
    features: [
      "Connect and own your AI accounts",
      "Provider health and priority",
      "No vendor lock-in",
    ],
  },
] as const;

export function FeaturesSection() {
  return (
    <section id="features" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Features available today
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
            Only implemented capabilities. Roadmap items live in the Vision section below.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CATEGORIES.map((category) => (
            <Card
              key={category.title}
              className="transition-all duration-300 hover:-translate-y-1 hover:border-[var(--color-foreground)]/15 hover:shadow-lg"
            >
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-muted)]">
                  <category.icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <CardTitle className="text-xl">{category.title}</CardTitle>
                <ul className="mt-2 space-y-2 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                  {category.features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
              </CardHeader>
              {"providers" in category && category.providers ? (
                <CardContent className="flex flex-wrap gap-2 pt-0">
                  {category.providers.map((provider) => (
                    <ProviderBadge key={provider} name={provider} />
                  ))}
                </CardContent>
              ) : null}
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
