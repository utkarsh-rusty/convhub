import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { routingApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { useAuth } from "@/context/auth-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { getInitials } from "@/lib/utils";
import type { RoutingPolicyType } from "@/types/api";

const ROUTING_POLICY_LABELS: Record<RoutingPolicyType, string> = {
  owner_first: "Owner First",
  balanced: "Balanced",
  lowest_usage: "Lowest Usage",
  cheapest: "Cheapest",
  priority: "Priority",
};

export function SettingsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const canManage = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data: routing, isLoading: routingLoading } = useQuery({
    queryKey: ["routing-settings", activeWorkspaceId],
    queryFn: () => routingApi.getSettings(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  const updateRoutingMutation = useMutation({
    mutationFn: (policy: RoutingPolicyType) =>
      routingApi.updateSettings(activeWorkspaceId!, policy),
    onSuccess: () => {
      toast.success("Routing policy updated");
      void queryClient.invalidateQueries({ queryKey: ["routing-settings", activeWorkspaceId] });
    },
    onError: (error) => showApiError(error, "Unable to update routing policy"),
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Settings</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Account and workspace preferences
        </p>
      </div>

      <div className="space-y-6 px-6 py-6">
        <section className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4">
          <h3 className="mb-3 text-sm font-medium">Your account</h3>
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarFallback>{user ? getInitials(user.name) : "?"}</AvatarFallback>
            </Avatar>
            <div>
              <p className="font-medium">{user?.name}</p>
              <p className="text-sm text-[var(--color-muted-foreground)]">{user?.email}</p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4">
          <h3 className="mb-3 text-sm font-medium">Active workspace</h3>
          {activeWorkspace ? (
            <div className="space-y-1 text-sm">
              <p className="font-medium">{activeWorkspace.name}</p>
              <p className="text-[var(--color-muted-foreground)]">/{activeWorkspace.slug}</p>
              <p className="text-[var(--color-muted-foreground)] capitalize">
                Your role: {activeWorkspace.role}
              </p>
            </div>
          ) : (
            <p className="text-sm text-[var(--color-muted-foreground)]">No workspace selected.</p>
          )}
        </section>

        {activeWorkspaceId && (
          <section className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4">
            <h3 className="mb-3 text-sm font-medium">Routing Policy</h3>
            {routingLoading ? (
              <Skeleton className="h-10 w-full max-w-sm" />
            ) : (
              <div className="space-y-4">
                <div className="max-w-sm space-y-2">
                  <Label htmlFor="routing_policy">Routing Policy</Label>
                  <Select
                    value={routing?.routing_policy ?? "owner_first"}
                    disabled={!canManage || updateRoutingMutation.isPending}
                    onValueChange={(value: RoutingPolicyType) =>
                      updateRoutingMutation.mutate(value)
                    }
                  >
                    <SelectTrigger id="routing_policy">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(ROUTING_POLICY_LABELS) as RoutingPolicyType[]).map((policy) => (
                        <SelectItem key={policy} value={policy}>
                          {ROUTING_POLICY_LABELS[policy]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {routing?.preview && (
                  <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-muted)]/20 p-3 text-sm">
                    <p className="font-medium">Selection preview</p>
                    <p className="mt-1 text-[var(--color-muted-foreground)]">
                      {routing.preview.selected_provider} · {routing.preview.selected_model}
                    </p>
                    <p className="mt-1 text-[var(--color-muted-foreground)]">
                      {routing.preview.decision_reason}
                    </p>
                  </div>
                )}

                {!canManage && (
                  <p className="text-sm text-[var(--color-muted-foreground)]">
                    Only workspace owners and admins can change routing policy.
                  </p>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
