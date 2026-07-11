import {
  ArrowLeftRight,
  Coins,
  FolderKanban,
  GitBranch,
  GitCommit,
  HardDrive,
  Network,
  Package,
  Radio,
  Sparkles,
  Terminal,
  Users,
} from "lucide-react";

import { ProviderBadge } from "@/components/landing/provider-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CATEGORIES = [
  {
    title: "AI Collaboration",
    icon: Users,
    features: [
      "Shared workspaces and invitations",
      "Realtime streaming and presence",
      "Why: stop reconstructing context from Slack and Git alone",
    ],
  },
  {
    title: "Workspaces & Projects",
    icon: FolderKanban,
    features: [
      "Durable home for conversations and memory",
      "Default Project per workspace",
      "Why: collaboration needs a container, not a chat URL",
    ],
  },
  {
    title: "Conversation Branching",
    icon: GitBranch,
    features: [
      "Branch from any message",
      "Independent lineage without rewriting the main thread",
      "Why: ideas fork — memory should fork with them",
    ],
  },
  {
    title: "Commits & Context Packages",
    icon: GitCommit,
    features: [
      "Manual commits with Git-like hashes",
      "Immutable Context Packages per commit",
      "Restore into a new working conversation",
      "Why: milestones should be findable and reusable",
    ],
  },
  {
    title: "Repository Memory",
    icon: HardDrive,
    features: [
      "Deterministic project-state memory per repo branch",
      "Composed from ConvHub data — not LLM summaries",
      "Why: the next developer needs the current picture",
    ],
  },
  {
    title: "Coding Workspaces",
    icon: Package,
    features: [
      "Link repositories and branches",
      "Sync metadata and active developers",
      "Why: AI work sits next to code",
    ],
  },
  {
    title: "Claude Code Integration",
    icon: Terminal,
    features: [
      "Official Claude Code hooks for transcript deltas",
      "convhub push and convhub pull",
      "Why: handoff should be a command, not a scavenger hunt",
    ],
  },
  {
    title: "AI Handoff & Restore",
    icon: ArrowLeftRight,
    features: [
      "Paste-ready Claude Handoff Markdown",
      "Pull Package compose and export",
      "Context Restore from packages",
      "Why: a new session needs a deterministic brief",
    ],
  },
  {
    title: "Ownership-first routing",
    icon: Sparkles,
    features: [
      "Routes through the sender's own providers first",
      "Borrow when needed, with clear metadata",
      "Anthropic, OpenAI, Gemini, Groq, and Ollama",
    ],
    providers: ["OpenAI", "Anthropic", "Gemini", "Groq", "Ollama"] as const,
  },
  {
    title: "Budgets & providers",
    icon: Coins,
    features: [
      "Workspace budgets and credit ledger",
      "Connect and own your AI accounts",
      "No vendor lock-in",
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
] as const;

export function FeaturesSection() {
  return (
    <section id="features" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            What ships in MVP v1
          </h2>
          <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
            Capabilities grouped by outcome. Roadmap items live in the Vision section below.
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
