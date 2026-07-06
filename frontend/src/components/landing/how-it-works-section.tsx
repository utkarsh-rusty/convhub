const STEPS = [
  {
    title: "Create a workspace",
    body: "Start a team workspace for shared conversations, providers, and budgets.",
  },
  {
    title: "Open a project",
    body: "Projects are the permanent home for conversations, commits, and context packages.",
  },
  {
    title: "Invite team members",
    body: "Add collaborators with workspace roles and conversation participation.",
  },
  {
    title: "Connect AI providers",
    body: "Each person connects their own accounts — Claude, OpenAI, Gemini, Groq, or Ollama.",
  },
  {
    title: "Start shared conversations",
    body: "Chat together in one thread with realtime updates and ownership-first routing.",
  },
  {
    title: "Branch conversations",
    body: "Fork from any message to explore an idea without changing the main thread.",
  },
  {
    title: "Commit important milestones",
    body: "Save intentional commits with Git-like hashes so key moments are easy to find.",
  },
  {
    title: "Restore from a checkpoint",
    body: "Open an immutable Context Package and restore it into a new working conversation.",
  },
  {
    title: "Continue collaborating",
    body: "Keep working with budgets, borrowing, branch visualization, and live presence.",
  },
] as const;

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">How it works</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          The workflow available in ConvHub today — every step is implemented.
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
