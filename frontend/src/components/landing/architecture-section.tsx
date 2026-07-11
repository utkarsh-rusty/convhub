import { ArrowDown, Bot, Code2, Layers } from "lucide-react";

const LAYERS = [
  {
    title: "Developer",
    icon: Code2,
    summary:
      "Works in ConvHub and Claude Code. Runs git push / pull for code, and convhub push / pull for AI context.",
  },
  {
    title: "ConvHub",
    icon: Layers,
    summary:
      "Projects, conversations, coding repos, Repository Memory, Pull Package, Claude Handoff, routing, and realtime.",
  },
  {
    title: "AI Providers",
    icon: Bot,
    summary: "Claude, OpenAI, Gemini, Groq, Ollama — each user keeps ownership of their accounts.",
  },
] as const;

export function ArchitectureSection() {
  return (
    <section id="architecture" className="border-y border-[var(--color-border)] px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Architecture today</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Three layers that ship in MVP v1. Repository metadata and Claude handoff are included;
          remote Git automation remains planned.
        </p>

        <div className="mt-12 flex flex-col items-stretch gap-3 md:mx-auto md:max-w-xl">
          {LAYERS.map((layer, index) => (
            <div key={layer.title}>
              <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] px-5 py-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--color-muted)]">
                    <layer.icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold">{layer.title}</h3>
                    <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">
                      {layer.summary}
                    </p>
                  </div>
                </div>
              </div>
              {index < LAYERS.length - 1 ? (
                <div className="flex justify-center py-1 text-[var(--color-muted-foreground)]">
                  <ArrowDown className="h-4 w-4" aria-hidden="true" />
                </div>
              ) : null}
            </div>
          ))}
        </div>

        <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-dashed border-[var(--color-border)] px-5 py-4 font-mono text-sm leading-7 text-[var(--color-muted-foreground)]">
          Workspace
          <br />
          &nbsp;&nbsp;↓
          <br />
          Projects
          <br />
          &nbsp;&nbsp;↓
          <br />
          Conversations / Repositories
          <br />
          &nbsp;&nbsp;↓
          <br />
          Commits → Context Packages
          <br />
          Repo Memory → Pull Package → Claude Handoff
        </div>
      </div>
    </section>
  );
}
