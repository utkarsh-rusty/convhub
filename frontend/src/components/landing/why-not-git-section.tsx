const ROWS = [
  { git: "Stores files", convhub: "Stores shared conversations" },
  { git: "Commit history", convhub: "Conversation commits & checkpoints" },
  { git: "Branches", convhub: "Conversation branches & lineage" },
  { git: "Diffs", convhub: "Message history & execution metadata" },
  { git: "Repository history", convhub: "Branch visualization & commit graph" },
] as const;

export function WhyNotGitSection() {
  return (
    <section id="why-not-git" className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Why not just Git?</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Git is perfect for code. ConvHub today versions the conversations, commits, and branches
          where AI-assisted decisions happen.
        </p>

        <div className="mt-12 overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)]">
          <div className="grid grid-cols-2 border-b border-[var(--color-border)] bg-[var(--color-muted)]/40 px-4 py-3 text-sm font-semibold">
            <div>Git</div>
            <div>ConvHub</div>
          </div>
          {ROWS.map((row) => (
            <div
              key={row.git}
              className="grid grid-cols-2 border-b border-[var(--color-border)] px-4 py-3 text-sm last:border-b-0"
            >
              <div className="pr-4 text-[var(--color-muted-foreground)]">{row.git}</div>
              <div className="pr-4">{row.convhub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
