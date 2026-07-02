import { MockBrowser } from "@/components/landing/mock-browser";
import { Skeleton } from "@/components/ui/skeleton";

const SHOWCASES = [
  {
    title: "convhub.app — Dashboard",
    label: "Dashboard",
    content: <DashboardMock />,
  },
  {
    title: "convhub.app — Conversation",
    label: "Conversation",
    content: <ConversationMock />,
  },
  {
    title: "convhub.app — Budget",
    label: "Budget",
    content: <BudgetMock />,
  },
  {
    title: "convhub.app — Routing",
    label: "Routing",
    content: <RoutingMock />,
  },
  {
    title: "convhub.app — Providers",
    label: "Providers",
    content: <ProvidersMock />,
  },
  {
    title: "convhub.app — Resource Sharing",
    label: "Resource Sharing",
    content: <SharingMock />,
  },
] as const;

export function ProductShowcase() {
  return (
    <section id="showcase" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Product showcase</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Realistic UI placeholders — swap in screenshots as the product matures.
        </p>

        <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {SHOWCASES.map((item) => (
            <figure key={item.label}>
              <MockBrowser title={item.title}>{item.content}</MockBrowser>
              <figcaption className="mt-3 text-center text-sm text-[var(--color-muted-foreground)]">
                {item.label}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}

function DashboardMock() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {["Members", "Credits", "Providers"].map((label) => (
          <div key={label} className="rounded-lg border border-[var(--color-border)] p-2">
            <p className="text-[10px] text-[var(--color-muted-foreground)]">{label}</p>
            <Skeleton className="mt-2 h-4 w-12" />
          </div>
        ))}
      </div>
      <Skeleton className="h-20 w-full rounded-lg" />
    </div>
  );
}

function ConversationMock() {
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Skeleton className="h-6 w-6 rounded-full" />
        <Skeleton className="h-10 flex-1 rounded-lg rounded-tl-none" />
      </div>
      <div className="ml-8">
        <Skeleton className="h-14 w-full rounded-lg border border-[var(--color-border)]" />
      </div>
      <Skeleton className="h-8 w-full rounded-md" />
    </div>
  );
}

function BudgetMock() {
  return (
    <div className="space-y-2">
      <Skeleton className="h-3 w-full rounded-full" />
      <div className="flex justify-between text-[10px] text-[var(--color-muted-foreground)]">
        <span>Used</span>
        <span>Remaining</span>
      </div>
      {[1, 2, 3].map((row) => (
        <Skeleton key={row} className="h-6 w-full rounded" />
      ))}
    </div>
  );
}

function RoutingMock() {
  return (
    <div className="space-y-2">
      {["Priority", "Balanced", "Cheapest"].map((policy) => (
        <div
          key={policy}
          className="flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2 text-xs"
        >
          <span>{policy}</span>
          <span className="h-3 w-3 rounded-full border border-[var(--color-border)]" />
        </div>
      ))}
    </div>
  );
}

function ProvidersMock() {
  return (
    <div className="space-y-2">
      {["Anthropic", "Groq", "OpenAI"].map((provider) => (
        <div
          key={provider}
          className="flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2 text-xs"
        >
          <span>{provider}</span>
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-600 dark:text-emerald-300">
            active
          </span>
        </div>
      ))}
    </div>
  );
}

function SharingMock() {
  return (
    <div className="space-y-2">
      {["Alice", "Bob", "Charlie"].map((name) => (
        <div key={name} className="flex items-center gap-2 text-xs">
          <Skeleton className="h-6 w-6 rounded-full" />
          <span className="flex-1">{name}</span>
          <Skeleton className="h-4 w-10" />
        </div>
      ))}
    </div>
  );
}
