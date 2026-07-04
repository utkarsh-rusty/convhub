const COMING_SOON = [
  "VS Code extension",
  "Git integration",
  "Decision Tracking",
  "Knowledge Graph",
  "Conversation Merge",
] as const;

export function FutureSection() {
  return (
    <section id="future" className="border-t border-[var(--color-border)] px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Designed for the future</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          The foundation is live. These capabilities are on the roadmap and are{" "}
          <span className="font-medium text-[var(--color-foreground)]">not implemented yet</span>.
        </p>

        <ul className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {COMING_SOON.map((item) => (
            <li
              key={item}
              className="flex items-center justify-between rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3 text-sm"
            >
              <span>{item}</span>
              <span className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                Coming soon
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
