import { Check, CircleDashed, FlaskConical } from "lucide-react";

const VERSIONS = [
  {
    version: "v1.0",
    status: "Implemented" as const,
    items: [
      "Collaborative workspace",
      "Ownership-first routing",
      "Borrowing engine",
      "Branching & commits",
      "Branch visualization",
      "Realtime collaboration",
    ],
  },
  {
    version: "v1.1–v1.4",
    status: "Planned" as const,
    items: [
      "Project memory & context packages",
      "Git metadata & linkage",
      "VS Code extension",
      "IDE adapters",
    ],
  },
  {
    version: "v2.0",
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
          Built in public. v1.0 is live. Later versions are planned or research — never described as
          shipped.
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
