import { useState } from "react";
import {
  ArrowDown,
  Brain,
  Building2,
  Coins,
  Factory,
  MessageSquare,
  Radio,
  Route,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";

const NODES = [
  {
    id: "workspace",
    title: "Workspace",
    icon: Building2,
    summary: "Team boundary for members, roles, and budgets.",
    detail: "Every request is scoped to a workspace with owner, admin, and member roles.",
  },
  {
    id: "conversation",
    title: "Conversation",
    icon: MessageSquare,
    summary: "Shared thread with participants and history.",
    detail: "Multiple teammates collaborate in one conversation with full message history.",
  },
  {
    id: "participants",
    title: "Participants",
    icon: Users,
    summary: "Who is in the thread — and who can lend providers.",
    detail: "Borrowing is limited to conversation participants who opted into auto-share.",
  },
  {
    id: "prompt",
    title: "Prompt Builder",
    icon: Brain,
    summary: "Assembles context for the model.",
    detail: "Messages, system context, and workspace policy become a provider-ready prompt.",
  },
  {
    id: "routing",
    title: "Ownership-first Routing",
    icon: Route,
    summary: "Uses the sender's AI accounts first.",
    detail: "Routing policy selects among the sender's active providers before any fallback.",
  },
  {
    id: "sender",
    title: "Sender Providers",
    icon: Factory,
    summary: "The sender's own Claude, GPT, Groq, or Ollama accounts.",
    detail: "Each user connects and owns their providers — ConvHub never replaces that ownership.",
  },
  {
    id: "borrow",
    title: "Borrow Engine",
    icon: Coins,
    summary: "Only when the sender has no usable provider.",
    detail: "Finds an eligible participant lender with remaining share credits.",
  },
  {
    id: "llm",
    title: "LLM Provider",
    icon: Factory,
    summary: "Executes the request and streams tokens.",
    detail: "Anthropic, OpenAI, Gemini, Groq, Ollama, and Mock share one abstraction.",
  },
  {
    id: "message",
    title: "Assistant Message",
    icon: MessageSquare,
    summary: "Persisted reply with execution metadata.",
    detail: "Own provider vs borrowed provider is recorded for transparency.",
  },
  {
    id: "realtime",
    title: "Realtime Broadcast",
    icon: Radio,
    summary: "Everyone sees updates instantly.",
    detail: "WebSockets deliver messages, streaming tokens, presence, and credit events.",
  },
] as const;

export function ArchitectureSection() {
  const [activeId, setActiveId] = useState<string | null>(null);

  return (
    <section id="architecture" className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Architecture</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          From shared conversation to assistant reply — ownership-first, borrow only when needed.
        </p>

        <div className="mt-12 hidden flex-col items-center gap-2 md:flex">
          {NODES.map((node, index) => (
            <div key={node.id} className="flex w-full max-w-xl flex-col items-center">
              <ArchitectureCard
                node={node}
                expanded={activeId === node.id}
                onActivate={() => setActiveId(node.id)}
              />
              {index < NODES.length - 1 ? (
                <ArrowDown className="my-1 h-4 w-4 text-[var(--color-muted-foreground)]" aria-hidden="true" />
              ) : null}
            </div>
          ))}
        </div>

        <div
          className="mt-12 flex gap-4 overflow-x-auto pb-4 md:hidden"
          role="list"
          aria-label="Architecture flow"
        >
          {NODES.map((node) => (
            <ArchitectureCard
              key={node.id}
              node={node}
              expanded={activeId === node.id}
              onActivate={() => setActiveId(node.id)}
              className="min-w-[260px] shrink-0"
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function ArchitectureCard({
  node,
  expanded,
  onActivate,
  className,
}: {
  node: (typeof NODES)[number];
  expanded: boolean;
  onActivate: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onActivate}
      onFocus={onActivate}
      onMouseEnter={onActivate}
      className={cn(
        "w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-5 text-left transition-all duration-300 hover:border-[var(--color-foreground)]/20 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-ring)]",
        expanded && "border-[var(--color-foreground)]/25 shadow-lg",
        className,
      )}
      aria-expanded={expanded}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-muted)]">
          <node.icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="text-lg font-semibold">{node.title}</p>
          <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">{node.summary}</p>
          <p
            className={cn(
              "mt-2 text-sm leading-relaxed text-[var(--color-muted-foreground)] transition-all duration-300",
              expanded ? "max-h-24 opacity-100" : "max-h-0 overflow-hidden opacity-0",
            )}
          >
            {node.detail}
          </p>
        </div>
      </div>
    </button>
  );
}
