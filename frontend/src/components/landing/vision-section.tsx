import { Check, CircleDashed, FlaskConical, Square } from "lucide-react";

const TODAY = [
  "Shared AI conversations",
  "Multi-provider routing",
  "Ownership-first provider routing",
  "Borrowing engine",
  "Conversation branching",
  "Conversation commits",
  "Context Packages",
  "Context Restore",
  "Branch visualization",
  "Realtime collaboration",
  "Budget management",
  "Open source",
] as const;

const NEXT = [
  "Decision Tracking",
  "Richer project memory timeline",
] as const;

const FUTURE = [
  "Git Integration",
  "Project objects",
  "VS Code Extension",
  "Claude Code Adapter",
  "Cursor Adapter",
  "Codex Adapter",
] as const;

const RESEARCH = [
  "Conversation Merge",
  "AI Merge Assistant",
  "Cross Repository Context",
  "Knowledge Graph",
] as const;

function Column({
  title,
  label,
  items,
  tone,
}: {
  title: string;
  label: string;
  items: readonly string[];
  tone: "implemented" | "planned" | "future" | "research";
}) {
  const Icon =
    tone === "implemented"
      ? Check
      : tone === "research"
        ? FlaskConical
        : tone === "planned"
          ? CircleDashed
          : Square;

  return (
    <div
      className={
        tone === "implemented"
          ? "rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-5"
          : "rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-card)] p-5"
      }
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-base font-semibold">{title}</h3>
        <span className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
          {label}
        </span>
      </div>
      <ul className="mt-4 space-y-2.5">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2.5 text-sm">
            <Icon
              className={
                tone === "implemented"
                  ? "mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400"
                  : "mt-0.5 h-4 w-4 shrink-0 text-[var(--color-muted-foreground)]"
              }
              aria-hidden="true"
            />
            <span
              className={
                tone === "implemented" ? "" : "text-[var(--color-muted-foreground)]"
              }
            >
              {item}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function VisionSection() {
  return (
    <section id="vision" className="border-t border-[var(--color-border)] px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-[var(--color-muted-foreground)]">
          Vision
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
          Where ConvHub is going
        </h2>
        <p className="mt-4 max-w-3xl text-lg text-[var(--color-muted-foreground)]">
          Git versions code. ConvHub versions project knowledge.
        </p>
        <p className="mt-3 max-w-3xl text-sm text-[var(--color-muted-foreground)]">
          The long-term direction is clear. Only the{" "}
          <span className="font-medium text-[var(--color-foreground)]">Today</span> column is
          available in the product now. Everything else is roadmap — not shipped.
        </p>

        <div className="mt-12 grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
          <Column title="Today" label="Implemented" items={TODAY} tone="implemented" />
          <Column title="Next" label="Planned" items={NEXT} tone="planned" />
          <Column title="Future" label="Planned" items={FUTURE} tone="future" />
          <Column title="Research" label="Research" items={RESEARCH} tone="research" />
        </div>
      </div>
    </section>
  );
}
