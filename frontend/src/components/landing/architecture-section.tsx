import { ArrowDown, Bot, Code2, Layers } from "lucide-react";

const LAYERS = [
  {
    title: "Developer",
    icon: Code2,
    summary: "Creates workspaces, invites teammates, connects providers, chats, branches, and commits.",
  },
  {
    title: "ConvHub",
    icon: Layers,
    summary:
      "Shared conversations, ownership-first routing, borrowing, budgets, commits, branches, and realtime.",
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
          Three layers that ship in the current product. Git repository linkage is planned and is
          not part of this diagram.
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
      </div>
    </section>
  );
}
