import {
  Coins,
  GitBranch,
  MessageSquare,
  Radio,
  Server,
  Sparkles,
} from "lucide-react";

import { ProviderBadge } from "@/components/landing/provider-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: MessageSquare,
    title: "Shared Conversations",
    description: "Everyone collaborates in one conversation.",
  },
  {
    icon: GitBranch,
    title: "Smart Routing",
    description: "Automatically choose the best available AI account.",
  },
  {
    icon: Coins,
    title: "Budget Governance",
    description: "Workspace credits, borrowing, spending, and allocation.",
  },
  {
    icon: Sparkles,
    title: "Multiple Providers",
    description: "Route across the providers your team already uses.",
    providers: ["OpenAI", "Anthropic", "Gemini", "Groq", "Ollama"] as const,
  },
  {
    icon: Radio,
    title: "Real-time Collaboration",
    description: "Typing indicators, presence, streaming responses, WebSockets.",
  },
  {
    icon: Server,
    title: "Open Source",
    description: "Docker, REST API, modern architecture, MIT License.",
  },
] as const;

export function FeaturesSection() {
  return (
    <section id="features" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Core features</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Built for engineering teams who need shared context, governed spend, and provider flexibility.
        </p>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <Card
              key={feature.title}
              className="transition-all duration-300 hover:-translate-y-1 hover:border-[var(--color-foreground)]/15 hover:shadow-lg"
            >
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-muted)]">
                  <feature.icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
                <CardDescription className="text-base leading-relaxed">
                  {feature.description}
                </CardDescription>
              </CardHeader>
              {"providers" in feature && feature.providers ? (
                <CardContent className="flex flex-wrap gap-2 pt-0">
                  {feature.providers.map((provider) => (
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
