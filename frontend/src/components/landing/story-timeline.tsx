import { Fragment } from "react";
import { ArrowDown, GitBranch, KeyRound, MessageSquareOff, Users } from "lucide-react";

const STEPS: Array<{
  icon: typeof MessageSquareOff;
  title: string;
  subtitle: string;
  highlight?: boolean;
}> = [
  {
    icon: MessageSquareOff,
    title: "Teams use ChatGPT.",
    subtitle: "Everyone has different conversations.",
  },
  {
    icon: KeyRound,
    title: "Different providers.",
    subtitle: "Different API keys. Different budgets.",
  },
  {
    icon: GitBranch,
    title: "Knowledge becomes fragmented.",
    subtitle: "Context lives in silos across tools and tabs.",
  },
  {
    icon: Users,
    title: "ConvHub creates one shared AI workspace.",
    subtitle: "One place for conversations, routing, and credits.",
    highlight: true,
  },
];

export function StoryTimeline() {
  return (
    <section className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-center text-3xl font-semibold tracking-tight md:text-4xl">
          Why ConvHub exists
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-[var(--color-muted-foreground)]">
          A short story of how team AI usage breaks down — and how ConvHub fixes it.
        </p>

        <ol className="mt-14 flex list-none flex-col gap-6 p-0 md:flex-row md:items-stretch md:gap-4">
          {STEPS.map((step, index) => (
            <Fragment key={step.title}>
              <li
                className={`flex flex-1 flex-col rounded-2xl border p-6 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg ${
                  step.highlight
                    ? "border-[var(--color-foreground)]/20 bg-[var(--color-card)] shadow-md"
                    : "border-[var(--color-border)] bg-[var(--color-card)]/60"
                }`}
              >
                <div
                  className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl ${
                    step.highlight ? "bg-[var(--color-foreground)] text-[var(--color-background)]" : "bg-[var(--color-muted)]"
                  }`}
                  aria-hidden="true"
                >
                  <step.icon className="h-5 w-5" />
                </div>
                <p className="text-lg font-semibold leading-snug">{step.title}</p>
                <p className="mt-2 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                  {step.subtitle}
                </p>
              </li>
              {index < STEPS.length - 1 ? (
                <li
                  className="flex list-none items-center justify-center md:flex-col"
                  aria-hidden="true"
                >
                  <ArrowDown className="h-5 w-5 text-[var(--color-muted-foreground)] md:rotate-[-90deg]" />
                </li>
              ) : null}
            </Fragment>
          ))}
        </ol>
      </div>
    </section>
  );
}
