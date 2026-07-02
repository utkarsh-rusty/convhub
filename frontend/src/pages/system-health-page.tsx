import { useQuery } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { Activity, RefreshCw, TestTube } from "lucide-react";
import { toast } from "sonner";

import { aiAccountApi, getErrorMessage, showApiError, systemApi } from "@/lib/api";
import { formatCredits, formatModelLabel, formatTimestamp, providerStatusLabel } from "@/lib/format";
import { useSocket } from "@/context/socket-context";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function StatusBadge({ status }: { status: string }) {
  const healthy = status === "healthy";
  const degraded = status === "degraded";
  return (
    <span
      className={
        healthy
          ? "rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-400"
          : degraded
            ? "rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-400"
            : "rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-400"
      }
    >
      {status}
    </span>
  );
}

export function SystemHealthPage() {
  const { activeWorkspace, activeWorkspaceId, isLoading: workspacesLoading } = useWorkspace();
  const { status: socketStatus } = useSocket();
  const canManage = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["system-status", activeWorkspaceId],
    queryFn: () => systemApi.getStatus(),
    enabled: Boolean(activeWorkspaceId && canManage && !workspacesLoading),
    refetchInterval: 30_000,
  });

  const testMutation = useMutation({
    mutationFn: aiAccountApi.test,
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
      void refetch();
    },
    onError: (error) => showApiError(error, "Unable to test provider"),
  });

  if (workspacesLoading) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <Skeleton className="h-64 w-full max-w-3xl" />
      </div>
    );
  }

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to view system health.
      </div>
    );
  }

  if (!canManage) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Only workspace owners and admins can view system health.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">System Health</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Infrastructure and provider status for this workspace
          </p>
        </div>
        <Button variant="outline" size="sm" disabled={isFetching} onClick={() => void refetch()}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : isError ? (
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-center">
            <p className="text-sm text-[var(--color-destructive)]">
              {getErrorMessage(error, "Unable to load system health")}
            </p>
            <Button className="mt-4" variant="outline" size="sm" onClick={() => void refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try again
            </Button>
          </div>
        ) : !data ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <div className="space-y-8">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.components.map((component) => (
                <div
                  key={component.name}
                  className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Activity className="h-4 w-4 text-[var(--color-muted-foreground)]" />
                      <h3 className="font-medium">{component.name}</h3>
                    </div>
                    <StatusBadge status={component.status} />
                  </div>
                  {component.detail ? (
                    <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">{component.detail}</p>
                  ) : null}
                </div>
              ))}
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-medium">Client WebSocket</h3>
                  <StatusBadge
                    status={
                      socketStatus === "connected"
                        ? "healthy"
                        : socketStatus === "connecting" || socketStatus === "reconnecting"
                          ? "degraded"
                          : "unhealthy"
                    }
                  />
                </div>
                <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                  Browser connection: {socketStatus}
                </p>
              </div>
            </div>

            <div>
              <h3 className="mb-3 text-base font-semibold">AI Providers</h3>
              {data.providers.length === 0 ? (
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  No AI providers configured. Add one from the AI Providers page.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-[var(--color-border)]">
                  <table className="w-full min-w-[960px] text-left text-sm">
                    <thead className="border-b border-[var(--color-border)] bg-[var(--color-muted)]/30">
                      <tr>
                        <th className="px-4 py-3 font-medium">Provider</th>
                        <th className="px-4 py-3 font-medium">Model</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                        <th className="px-4 py-3 font-medium">Last Used</th>
                        <th className="px-4 py-3 font-medium">Requests</th>
                        <th className="px-4 py-3 font-medium">Credits Used</th>
                        <th className="px-4 py-3 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.providers.map((provider) => (
                        <tr
                          key={provider.account_id}
                          className="border-b border-[var(--color-border)] last:border-0"
                        >
                          <td className="px-4 py-3">
                            <p className="font-medium capitalize">{provider.provider}</p>
                            <p className="text-xs text-[var(--color-muted-foreground)]">
                              {provider.display_name}
                            </p>
                          </td>
                          <td className="px-4 py-3">
                            {formatModelLabel(provider.model, provider.provider)}
                          </td>
                          <td className="px-4 py-3">
                            {provider.healthy
                              ? providerStatusLabel(true, provider.request_count)
                              : "Unhealthy"}
                          </td>
                          <td className="px-4 py-3">
                            {provider.last_used_at
                              ? formatTimestamp(provider.last_used_at)
                              : "Never"}
                          </td>
                          <td className="px-4 py-3">{provider.request_count}</td>
                          <td className="px-4 py-3">{formatCredits(provider.credits_used)}</td>
                          <td className="px-4 py-3">
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={testMutation.isPending}
                              onClick={() => testMutation.mutate(provider.account_id)}
                            >
                              <TestTube className="mr-2 h-4 w-4" />
                              Test
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
