import { Check, CircleDashed, FlaskConical } from "lucide-react";

const VERSIONS = [
  {
    version: "MVP v1",
    status: "Implemented" as const,
    items: [
      "Collaborative workspaces & projects",
      "Ownership-first routing & borrowing",
      "Branching, commits, Context Packages & restore",
      "Coding workspaces & Repository Memory",
      "Claude Code plugin (convhub push / pull)",
      "Realtime collaboration",
    ],
  },
  {
    version: "Next / Future",
    status: "Planned" as const,
    items: [
      "Decision Tracking & richer memory UX",
      "Optional AI summaries",
      "VS Code extension",
      "Codex / Gemini / Cursor adapters",
      "Git automation & enterprise",
    ],
  },
  {
    version: "Research",
    status: "Research" as const,
    items: [
      "Semantic context restore",
      "Conversation merge",
      "Knowledge graph",
      "Cross-repository memory",
    ],
  },
] as const;

function StatusIcon({ status }: { status: "Implemented" | "Planned" | "Research" }) {
  if (status === "Implemented") {
    return <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />;
  }
  if (status === "Planned") {
    return <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-muted-foreground)]" />;
  }
  return <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-muted-foreground)]" />;
}

export function RoadmapSection() {
  return (
    <section id="roadmap" className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Roadmap</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Built in public. MVP v1 through Sprint 36 is complete. Later work is planned or research —
          never described as shipped.
        </p>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {VERSIONS.map((block) => (
            <div
              key={block.version}
              className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-6"
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-lg font-semibold">{block.version}</h3>
                <span className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                  {block.status}
                </span>
              </div>
              <ul className="mt-4 space-y-3">
                {block.items.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <StatusIcon status={block.status} />
                    <span
                      className={
                        block.status === "Implemented"
                          ? ""
                          : "text-[var(--color-muted-foreground)]"
                      }
                    >
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
