import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { sharingApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

function formatCredits(value: string) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function ResourceSharingPage() {
  const queryClient = useQueryClient();
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const canManage = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data: preferences, isLoading: preferencesLoading } = useQuery({
    queryKey: ["sharing-me", activeWorkspaceId],
    queryFn: () => sharingApi.getMyPreferences(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["sharing-overview", activeWorkspaceId],
    queryFn: () => sharingApi.getWorkspaceOverview(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId) && canManage,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: {
      auto_share_enabled?: boolean;
      monthly_share_limit?: string;
      minimum_reserved_credits?: string;
    }) => sharingApi.updateMyPreferences(activeWorkspaceId!, payload),
    onSuccess: () => {
      toast.success("Sharing preferences updated");
      void queryClient.invalidateQueries({ queryKey: ["sharing-me", activeWorkspaceId] });
      if (canManage) {
        void queryClient.invalidateQueries({ queryKey: ["sharing-overview", activeWorkspaceId] });
      }
    },
    onError: (error) => showApiError(error, "Unable to update sharing preferences"),
  });

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to configure resource sharing.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Resource Sharing</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Share unused credits with teammates when you opt in
        </p>
      </div>

      <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
        <section className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-4">
          <h3 className="mb-4 text-sm font-medium">Your sharing preferences</h3>
          {preferencesLoading || !preferences ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <Label htmlFor="auto-share">Auto Share</Label>
                  <p className="text-sm text-[var(--color-muted-foreground)]">
                    Allow teammates to borrow from your balance when theirs is exhausted
                  </p>
                </div>
                <input
                  id="auto-share"
                  type="checkbox"
                  className="h-4 w-4 rounded border border-[var(--color-border)]"
                  checked={preferences.auto_share_enabled}
                  onChange={(event) =>
                    updateMutation.mutate({ auto_share_enabled: event.target.checked })
                  }
                  disabled={updateMutation.isPending}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="share-limit">Monthly Share Limit</Label>
                  <Input
                    id="share-limit"
                    type="number"
                    min={0}
                    step="0.01"
                    defaultValue={preferences.monthly_share_limit}
                    key={`limit-${preferences.updated_at}`}
                    onBlur={(event) => {
                      const value = event.target.value;
                      if (value && value !== preferences.monthly_share_limit) {
                        updateMutation.mutate({ monthly_share_limit: value });
                      }
                    }}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="min-reserve">Minimum Reserve</Label>
                  <Input
                    id="min-reserve"
                    type="number"
                    min={0}
                    step="0.01"
                    defaultValue={preferences.minimum_reserved_credits}
                    key={`reserve-${preferences.updated_at}`}
                    onBlur={(event) => {
                      const value = event.target.value;
                      if (value && value !== preferences.minimum_reserved_credits) {
                        updateMutation.mutate({ minimum_reserved_credits: value });
                      }
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </section>

        {canManage ? (
          <section>
            <h3 className="mb-3 text-sm font-medium">Workspace sharing overview</h3>
            {overviewLoading ? (
              <Skeleton className="h-48 w-full" />
            ) : overview && overview.members.length > 0 ? (
              <div className="overflow-x-auto rounded-lg border border-[var(--color-border)]">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="border-b border-[var(--color-border)] bg-[var(--color-muted)]/30">
                    <tr>
                      <th className="px-4 py-3 font-medium">Member</th>
                      <th className="px-4 py-3 font-medium">Remaining</th>
                      <th className="px-4 py-3 font-medium">Share Limit</th>
                      <th className="px-4 py-3 font-medium">Reserve</th>
                      <th className="px-4 py-3 font-medium">Borrowed</th>
                      <th className="px-4 py-3 font-medium">Lent</th>
                      <th className="px-4 py-3 font-medium">Auto Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.members.map((member) => (
                      <tr
                        key={member.user_id}
                        className="border-b border-[var(--color-border)] last:border-0"
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium">{member.user_name}</p>
                          <p className="text-xs text-[var(--color-muted-foreground)]">
                            {member.user_email}
                          </p>
                        </td>
                        <td className="px-4 py-3">{formatCredits(member.remaining_credits)}</td>
                        <td className="px-4 py-3">{formatCredits(member.monthly_share_limit)}</td>
                        <td className="px-4 py-3">
                          {formatCredits(member.minimum_reserved_credits)}
                        </td>
                        <td className="px-4 py-3">{formatCredits(member.borrowed_credits)}</td>
                        <td className="px-4 py-3">{formatCredits(member.lent_credits)}</td>
                        <td className="px-4 py-3">{member.auto_share_enabled ? "Yes" : "No"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">No members found.</p>
            )}
          </section>
        ) : null}
      </div>
    </div>
  );
}
