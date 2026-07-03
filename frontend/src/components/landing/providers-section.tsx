import { ProviderBadge } from "@/components/landing/provider-badge";

const PROVIDERS = ["Anthropic", "OpenAI", "Gemini", "Groq", "Ollama"] as const;

export function ProvidersSection() {
  return (
    <section id="providers" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Built for any AI</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          ConvHub is provider-agnostic. Ownership-first routing uses each developer&apos;s own
          accounts — Claude, OpenAI, Gemini, Groq, or local Ollama — without locking the team to a
          single vendor.
        </p>

        <div className="mt-10 flex flex-wrap gap-3">
          {PROVIDERS.map((provider) => (
            <ProviderBadge key={provider} name={provider} />
          ))}
        </div>
      </div>
    </section>
  );
}
