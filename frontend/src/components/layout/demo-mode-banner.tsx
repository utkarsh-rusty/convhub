import { useQuery } from "@tanstack/react-query";

import { demoApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";

export function DemoModeBanner() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();

  const { data: demoConfig } = useQuery({
    queryKey: ["demo-config"],
    queryFn: () => demoApi.getConfig(),
    staleTime: 60_000,
  });

  const { data: demoSettings } = useQuery({
    queryKey: ["demo-settings", activeWorkspaceId],
    queryFn: () => demoApi.getSettings(activeWorkspaceId!),
    enabled: Boolean(demoConfig?.enabled && activeWorkspaceId),
    retry: false,
  });

  if (!demoConfig?.enabled) {
    return null;
  }

  return (
    <div className="flex items-center gap-4 border-b border-amber-500/30 bg-amber-500/10 px-6 py-2 text-sm">
      <span className="font-medium text-amber-700 dark:text-amber-300">🟡 DEMO MODE</span>
      <span className="text-[var(--color-muted-foreground)]">
        Pricing:{" "}
        <span className="font-medium text-[var(--color-foreground)]">
          {demoSettings?.pricing_profile ?? "production"}
        </span>
      </span>
      <span className="text-[var(--color-muted-foreground)]">
        Workspace:{" "}
        <span className="font-medium text-[var(--color-foreground)]">
          {activeWorkspace?.name ?? "—"}
        </span>
      </span>
    </div>
  );
}
