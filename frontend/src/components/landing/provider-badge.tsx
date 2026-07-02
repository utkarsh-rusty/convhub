import { cn } from "@/lib/utils";

const PROVIDER_STYLES: Record<string, string> = {
  OpenAI: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
  Anthropic: "border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-300",
  Gemini: "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300",
  Groq: "border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  Ollama: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300",
};

export function ProviderBadge({ name }: { name: keyof typeof PROVIDER_STYLES | string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        PROVIDER_STYLES[name] ?? "border-[var(--color-border)] bg-[var(--color-muted)]",
      )}
    >
      {name}
    </span>
  );
}
