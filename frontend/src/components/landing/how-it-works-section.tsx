const STEPS = [
  {
    title: "Create a workspace",
    body: "Start a team workspace for shared conversations, providers, and budgets.",
  },
  {
    title: "Create a project",
    body: "Projects are the permanent home for conversations, repositories, and memory.",
  },
  {
    title: "Invite developers",
    body: "Add collaborators with workspace roles so everyone can pick up the same thread.",
  },
  {
    title: "Developer A works",
    body: "Collaborate in ConvHub and/or Claude Code. Connect providers you own.",
  },
  {
    title: "convhub push",
    body: "Upload transcript deltas and refresh Repository Memory, Pull Package, and handoff.",
  },
  {
    title: "Developer B: git pull",
    body: "Pull the latest code as usual. ConvHub does not replace Git.",
  },
  {
    title: "convhub pull",
    body: "Download a paste-ready Claude Handoff document for the repository branch.",
  },
  {
    title: "Paste into Claude Code",
    body: "Open a new Claude Code session and paste the handoff. Continue seamlessly.",
  },
  {
    title: "Branch, commit, restore",
    body: "Optionally branch conversations, commit milestones, and restore Context Packages.",
  },
] as const;

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">How it works</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          From workspace setup to Claude Code handoff — every step below ships in MVP v1.
        </p>

        <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)] p-5"
            >
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--color-muted-foreground)]">
                Step {index + 1}
              </p>
              <h3 className="mt-2 text-base font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                {step.body}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
