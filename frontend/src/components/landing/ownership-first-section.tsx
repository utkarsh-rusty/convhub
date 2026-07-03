import { ArrowDown } from "lucide-react";

import { ProviderBadge } from "@/components/landing/provider-badge";

const ALICE_PROVIDERS = ["Claude", "OpenAI", "Groq"] as const;

export function OwnershipFirstSection() {
  return (
    <section className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Ownership-first routing</h2>
          <p className="mt-4 text-[var(--color-muted-foreground)]">
            When you send a message, ConvHub uses your AI providers first. Borrowing only happens
            when you have no usable account — and only from someone in the same conversation who
            opted in to share.
          </p>
        </div>

        <div className="mx-auto mt-14 flex max-w-lg flex-col items-center gap-3">
          <div className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] px-5 py-4">
            <p className="font-semibold">Alice owns</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {ALICE_PROVIDERS.map((provider) => (
                <ProviderBadge key={provider} name={provider} />
              ))}
            </div>
          </div>

          <ArrowDown className="h-5 w-5 text-[var(--color-muted-foreground)]" aria-hidden="true" />

          <div className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] px-5 py-4 text-center">
            <p className="font-medium">Alice sends a message</p>
          </div>

          <ArrowDown className="h-5 w-5 text-[var(--color-muted-foreground)]" aria-hidden="true" />

          <div className="w-full rounded-2xl border border-[var(--color-foreground)]/20 bg-[var(--color-card)] px-5 py-4 text-center shadow-sm">
            <p className="font-medium">ConvHub uses Alice&apos;s providers</p>
          </div>

          <ArrowDown className="h-5 w-5 text-[var(--color-muted-foreground)]" aria-hidden="true" />

          <p className="text-sm font-medium text-[var(--color-muted-foreground)]">Only if none are available</p>

          <ArrowDown className="h-5 w-5 text-[var(--color-muted-foreground)]" aria-hidden="true" />

          <div className="w-full rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-muted)]/30 px-5 py-4 text-center">
            <p className="font-medium">Borrow Bob&apos;s provider</p>
            <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">
              Participant-only · auto-share on · credits remaining
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
