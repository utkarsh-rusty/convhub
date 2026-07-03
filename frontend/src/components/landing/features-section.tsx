import {
  Coins,
  MessageSquare,
  Radio,
  Server,
  Shield,
  Sparkles,
  Users,
} from "lucide-react";

import { ProviderBadge } from "@/components/landing/provider-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CATEGORIES = [
  {
    title: "Collaboration",
    icon: Users,
    features: [
      "Shared conversations with multiple participants",
      "Live collaboration, presence, and typing indicators",
      "Conversation permissions per workspace",
    ],
  },
  {
    title: "AI Orchestration",
    icon: Sparkles,
    features: [
      "Ownership-first routing across your providers",
      "Automatic failover and participant borrowing",
      "Anthropic, OpenAI, Gemini, Groq, and Ollama",
    ],
    providers: ["OpenAI", "Anthropic", "Gemini", "Groq", "Ollama"] as const,
  },
  {
    title: "Realtime",
    icon: Radio,
    features: [
      "WebSocket streaming responses",
      "Live credit and routing events",
      "Instant message sync for every participant",
    ],
  },
  {
    title: "Governance",
    icon: Coins,
    features: [
      "Workspace budgets and credit ledger",
      "Borrow limits and lending preferences",
      "Routing policies and AI account ownership",
    ],
  },
  {
    title: "Open Source",
    icon: Server,
    features: [
      "MIT licensed — clone and run locally",
      "Docker Compose for quick setup",
      "REST API and documented architecture",
    ],
  },
  {
    title: "Enterprise Ready",
    icon: Shield,
    features: [
      "JWT authentication and workspace isolation",
      "Role-based permissions and audit trail",
      "Provider abstraction — no vendor lock-in",
    ],
  },
] as const;

export function FeaturesSection() {
  return (
    <section id="features" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-muted)]">
            <MessageSquare className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Features</h2>
            <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
              Everything your team needs to collaborate on AI conversations — with governance built in.
            </p>
          </div>
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
