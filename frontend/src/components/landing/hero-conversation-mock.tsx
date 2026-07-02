import { useEffect, useState } from "react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

const PHASE_DURATION_MS = 2800;

type Phase = 0 | 1 | 2 | 3;

export function HeroConversationMock() {
  const reducedMotion = useReducedMotion();
  const [phase, setPhase] = useState<Phase>(reducedMotion ? 3 : 0);

  useEffect(() => {
    if (reducedMotion) {
      return;
    }

    const timer = window.setInterval(() => {
      setPhase((current) => ((current + 1) % 4) as Phase);
    }, PHASE_DURATION_MS);

    return () => window.clearInterval(timer);
  }, [reducedMotion]);

  return (
    <div
      className="relative mx-auto w-full max-w-lg"
      aria-label="Animated example of a collaborative AI conversation"
      role="img"
    >
      <div className="landing-glow pointer-events-none absolute -inset-8 rounded-3xl opacity-60" aria-hidden="true" />
      <div className="relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-card)]/80 p-5 shadow-2xl backdrop-blur-sm">
        <div className="mb-4 flex items-center justify-between border-b border-[var(--color-border)] pb-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--color-muted-foreground)]">
              Shared conversation
            </p>
            <p className="text-sm font-semibold">API error handling review</p>
          </div>
          <div className="flex -space-x-2">
            {["A", "B", "C"].map((initial) => (
              <Avatar key={initial} className="h-7 w-7 border-2 border-[var(--color-card)]">
                <AvatarFallback className="text-[10px]">{initial}</AvatarFallback>
              </Avatar>
            ))}
          </div>
        </div>

        <div className="space-y-3 text-sm">
          <MessageRow
            visible={phase >= 0}
            name="Alice"
            initials="A"
            content="Can someone review this answer?"
          />

          <TypingRow visible={phase === 1} name="Bob" />

          <AssistantRow
            visible={phase >= 2}
            provider="Groq"
            content="Here's an improved version with clearer error boundaries and retry logic."
          />

          <ReactionRow visible={phase >= 3} name="Charlie" />
        </div>
      </div>
    </div>
  );
}

function MessageRow({
  visible,
  name,
  initials,
  content,
}: {
  visible: boolean;
  name: string;
  initials: string;
  content: string;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 transition-all duration-500",
        visible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
      )}
    >
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback className="text-xs">{initials}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <p className="mb-1 text-xs font-medium text-[var(--color-muted-foreground)]">{name}</p>
        <p className="rounded-lg rounded-tl-none bg-[var(--color-muted)] px-3 py-2">{content}</p>
      </div>
    </div>
  );
}

function TypingRow({ visible, name }: { visible: boolean; name: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-xs text-[var(--color-muted-foreground)] transition-all duration-500",
        visible ? "opacity-100" : "h-0 overflow-hidden opacity-0",
      )}
      aria-live="polite"
    >
      <span className="font-medium text-[var(--color-foreground)]">{name}</span>
      <span>is typing</span>
      <span className="landing-typing-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
    </div>
  );
}

function AssistantRow({
  visible,
  provider,
  content,
}: {
  visible: boolean;
  provider: string;
  content: string;
}) {
  return (
    <div
      className={cn(
        "transition-all duration-500",
        visible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
      )}
    >
      <div className="mb-1 flex items-center gap-2">
        <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-xs font-medium text-violet-600 dark:text-violet-300">
          {provider}
        </span>
      </div>
      <p className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2">
        {content}
      </p>
    </div>
  );
}

function ReactionRow({ visible, name }: { visible: boolean; name: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 text-xs text-[var(--color-muted-foreground)] transition-all duration-500",
        visible ? "opacity-100" : "opacity-0",
      )}
    >
      <Avatar className="h-6 w-6">
        <AvatarFallback className="text-[10px]">{name[0]}</AvatarFallback>
      </Avatar>
      <span>
        <span className="font-medium text-[var(--color-foreground)]">{name}</span> reacted 👍
      </span>
    </div>
  );
}
