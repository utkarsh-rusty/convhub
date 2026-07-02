import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function MockBrowser({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] shadow-lg transition-transform duration-300 hover:-translate-y-1",
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] bg-[var(--color-muted)]/40 px-4 py-2.5">
        <div className="flex gap-1.5" aria-hidden="true">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        </div>
        <p className="ml-2 truncate text-xs text-[var(--color-muted-foreground)]">{title}</p>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}
