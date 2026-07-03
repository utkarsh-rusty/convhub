import { ArrowDown } from "lucide-react";

import { ProviderBadge } from "@/components/landing/provider-badge";

const PARTICIPANTS = [
  { name: "Alice", provider: "Claude" as const },
  { name: "Bob", provider: "Groq" as const },
  { name: "Charlie", provider: "OpenAI" as const },
] as const;

export function OneConversationSection() {
  return (
    <section className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl text-center">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
          One Conversation.
          <br />
          Any AI.
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Your team uses different models and API keys. ConvHub keeps everyone in the same thread.
        </p>

        <div className="mx-auto mt-14 flex max-w-md flex-col items-center gap-3">
          {PARTICIPANTS.map((participant) => (
            <div
              key={participant.name}
              className="flex w-full items-center justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] px-5 py-4"
            >
              <span className="font-medium">{participant.name}</span>
              <ProviderBadge name={participant.provider} />
            </div>
          ))}

          <ArrowDown className="my-2 h-5 w-5 text-[var(--color-muted-foreground)]" aria-hidden="true" />

          <div className="w-full rounded-2xl border border-[var(--color-foreground)]/20 bg-[var(--color-card)] px-5 py-4 shadow-md">
            <p className="font-semibold">Shared Conversation</p>
            <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">
              One thread. Full history. Every participant.
            </p>
          </div>

          <ArrowDown className="my-2 h-5 w-5 text-[var(--color-muted-foreground)]" aria-hidden="true" />

          <p className="text-lg font-medium">Everyone sees the same thread.</p>
        </div>
      </div>
    </section>
  );
}
