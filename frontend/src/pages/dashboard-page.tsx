import { useQuery } from "@tanstack/react-query";

import { budgetApi, routingApi, sharingApi, workspaceApi, aiAccountApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { useSocket } from "@/context/socket-context";
import { formatCredits, formatRoutingPolicy } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardPage() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const { status } = useSocket();
  const canViewOverview = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data: members = [], isLoading: membersLoading } = useQuery({
    queryKey: ["workspace-members", activeWorkspaceId],
    queryFn: () => workspaceApi.listMembers(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ["workspace-budget-settings", activeWorkspaceId],
    queryFn: () => budgetApi.getWorkspaceSettings(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && canViewOverview),
    refetchOnWindowFocus: false,
  });

  const { data: routing, isLoading: routingLoading } = useQuery({
    queryKey: ["routing-settings", activeWorkspaceId],
    queryFn: () => routingApi.getSettings(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
    refetchOnWindowFocus: false,
  });

  const { data: sharing, isLoading: sharingLoading } = useQuery({
    queryKey: ["sharing-overview", activeWorkspaceId],
    queryFn: () => sharingApi.getWorkspaceOverview(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && canViewOverview),
    refetchOnWindowFocus: false,
  });

  const { data: myBudget, isLoading: myBudgetLoading } = useQuery({
    queryKey: ["budget", activeWorkspaceId],
    queryFn: () => budgetApi.getMyBudget(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
    refetchOnWindowFocus: false,
  });

  const { data: myAccounts = [], isLoading: accountsLoading } = useQuery({
    queryKey: ["ai-accounts", activeWorkspaceId],
    queryFn: () => aiAccountApi.list(),
    enabled: Boolean(activeWorkspaceId),
    refetchOnWindowFocus: false,
  });

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to view the dashboard.
      </div>
    );
  }

  const defaultProvider =
    routing?.preview.selected_provider ??
    routing?.active_accounts[0]?.provider ??
    "—";

  const isLoading =
    membersLoading || settingsLoading || routingLoading || sharingLoading || myBudgetLoading || accountsLoading;
  const myProviders = myAccounts.filter((account) => account.is_mine);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Workspace Dashboard</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Overview of credits, routing, and team activity · Live {status}
        </p>
      </div>

      <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <SummaryCard label="Workspace" value={activeWorkspace?.name ?? "—"} />
              <SummaryCard label="Members" value={String(members.length)} />
              <SummaryCard
                label="My Providers"
                value={String(myProviders.length)}
                hint={
                  myProviders.length > 0
                    ? myProviders.map((account) => account.provider).join(", ")
                    : "Add providers in AI Providers"
                }
              />
              <SummaryCard
                label="Borrowed This Month"
                value={formatCredits(myBudget?.borrowed_credits ?? "0")}
              />
              <SummaryCard
                label="Shared This Month"
                value={formatCredits(myBudget?.lent_credits ?? "0")}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <SummaryCard
                label="Borrowing Budget"
                value={formatCredits(myBudget?.remaining_credits ?? "0")}
              />
              <SummaryCard
                label="Budget Status"
                value={
                  myBudget && Number(myBudget.remaining_credits) <= 0
                    ? "Exceeded"
                    : "Within limit"
                }
              />
              <SummaryCard
                label="Borrowing"
                value={settings?.allow_credit_borrowing ? "Enabled" : "Disabled"}
                hint={canViewOverview && !settings?.allow_credit_borrowing ? "Enable in Settings" : undefined}
              />
              <SummaryCard
                label="Routing Policy"
                value={formatRoutingPolicy(routing?.routing_policy ?? "owner_first")}
              />
            </div>

            {canViewOverview && sharing ? (
              <section>
                <h3 className="mb-3 text-sm font-medium">Team credits</h3>
                <div className="overflow-x-auto rounded-lg border border-[var(--color-border)]">
                  <table className="w-full min-w-[800px] text-left text-sm">
                    <thead className="border-b border-[var(--color-border)] bg-[var(--color-muted)]/30">
                      <tr>
                        <th className="px-4 py-3 font-medium">Member</th>
                        <th className="px-4 py-3 font-medium">Remaining Credits</th>
                        <th className="px-4 py-3 font-medium">Provider</th>
                        <th className="px-4 py-3 font-medium">Sharing</th>
                        <th className="px-4 py-3 font-medium">Borrowed</th>
                        <th className="px-4 py-3 font-medium">Lent</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sharing.members.map((member) => (
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
                          <td className="px-4 py-3 capitalize">{defaultProvider}</td>
                          <td className="px-4 py-3">
                            {member.auto_share_enabled ? "Enabled" : "Off"}
                          </td>
                          <td className="px-4 py-3">{formatCredits(member.borrowed_credits)}</td>
                          <td className="px-4 py-3">{formatCredits(member.lent_credits)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Ask a workspace owner or admin for the full team credits view.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
      <p className="text-sm text-[var(--color-muted-foreground)]">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
      {hint ? (
        <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">{hint}</p>
      ) : null}
    </div>
  );
}
