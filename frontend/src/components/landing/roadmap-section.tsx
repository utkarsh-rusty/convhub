import { Check, Square } from "lucide-react";

const COMPLETED = [
  "Shared AI Workspace",
  "Ownership Routing",
  "Borrow Engine",
  "Realtime Collaboration",
] as const;

const UPCOMING = [
  "Conversation Branching",
  "Fork Conversations",
  "Merge Conversations",
  "Conversation Import",
  "Shared Context Packs",
] as const;

export function RoadmapSection() {
  return (
    <section id="roadmap" className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Roadmap</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Built in public. Phase 1 is live; branching, import, and shared context are next.
        </p>

        <div className="mt-12 grid gap-8 md:grid-cols-2">
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-6">
            <h3 className="text-lg font-semibold">Completed</h3>
            <ul className="mt-4 space-y-3">
              {COMPLETED.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-6">
            <h3 className="text-lg font-semibold">Upcoming</h3>
            <ul className="mt-4 space-y-3">
              {UPCOMING.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-[var(--color-muted-foreground)]">
                  <Square className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
