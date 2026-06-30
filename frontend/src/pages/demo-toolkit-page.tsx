import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { aiAccountApi, demoApi, showApiError, workspaceApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import type {
  DemoSettingsResponse,
  PricingProfileType,
  ProviderSimulationMode,
  RoutingOverrideMode,
} from "@/types/api";

function formatCredits(value: string) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-5">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1 mb-4 text-sm text-[var(--color-muted-foreground)]">{description}</p>
      {children}
    </section>
  );
}

export function DemoToolkitPage() {
  const queryClient = useQueryClient();
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const canManage = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data: demoConfig } = useQuery({
    queryKey: ["demo-config"],
    queryFn: () => demoApi.getConfig(),
    staleTime: 60_000,
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ["demo-settings", activeWorkspaceId],
    queryFn: () => demoApi.getSettings(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && demoConfig?.enabled && canManage),
  });

  const { data: members = [] } = useQuery({
    queryKey: ["workspace-members", activeWorkspaceId],
    queryFn: () => workspaceApi.listMembers(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && demoConfig?.enabled && canManage),
  });

  const { data: budgets = [], isLoading: budgetsLoading } = useQuery({
    queryKey: ["demo-budgets", activeWorkspaceId],
    queryFn: () => demoApi.listBudgets(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && demoConfig?.enabled && canManage),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ["ai-accounts"],
    queryFn: () => aiAccountApi.list(),
    enabled: Boolean(activeWorkspaceId && demoConfig?.enabled && canManage),
  });

  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ["demo-events", activeWorkspaceId],
    queryFn: () => demoApi.listEvents(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && demoConfig?.enabled && canManage),
  });

  const invalidateDemo = () => {
    void queryClient.invalidateQueries({ queryKey: ["demo-settings", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["demo-budgets", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["demo-events", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["budget", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["credit-history", activeWorkspaceId] });
  };

  const settingsMutation = useMutation({
    mutationFn: async (payload: Partial<DemoSettingsResponse>) => {
      if (payload.pricing_profile) {
        return demoApi.updatePricingProfile(activeWorkspaceId!, payload.pricing_profile);
      }
      if (payload.provider_simulation) {
        return demoApi.updateProviderSimulation(activeWorkspaceId!, payload.provider_simulation);
      }
      if (payload.routing_override_mode) {
        return demoApi.updateRoutingOverride(activeWorkspaceId!, {
          routing_override_mode: payload.routing_override_mode,
          routing_override_account_id: payload.routing_override_account_id,
        });
      }
      throw new Error("No demo setting to update");
    },
    onSuccess: () => {
      toast.success("Demo settings updated");
      invalidateDemo();
    },
    onError: (error) => showApiError(error, "Unable to update demo settings"),
  });

  const actionMutation = useMutation({
    mutationFn: async (action: string) => {
      const workspaceId = activeWorkspaceId!;
      switch (action) {
        case "reset-all":
          return demoApi.resetAllCredits(workspaceId);
        case "clear-ledger":
          return demoApi.clearLedger(workspaceId);
        case "reseed":
          return demoApi.reseedAllocations(workspaceId);
        default:
          throw new Error("Unknown action");
      }
    },
    onSuccess: (result) => {
      toast.success(result.message);
      invalidateDemo();
    },
    onError: (error) => showApiError(error, "Demo action failed"),
  });

  const creditMutation = useMutation({
    mutationFn: ({ userId, remaining }: { userId: string; remaining: string }) =>
      demoApi.setUserCredits(activeWorkspaceId!, userId, remaining),
    onSuccess: () => {
      toast.success("Credits updated");
      invalidateDemo();
    },
    onError: (error) => showApiError(error, "Unable to set credits"),
  });

  const resetUserMutation = useMutation({
    mutationFn: (userId: string) => demoApi.resetUserCredits(activeWorkspaceId!, userId),
    onSuccess: () => {
      toast.success("User credits reset");
      invalidateDemo();
    },
    onError: (error) => showApiError(error, "Unable to reset user credits"),
  });

  if (!demoConfig?.enabled) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Demo mode is not enabled on this server.
      </div>
    );
  }

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to open the demo toolkit.
      </div>
    );
  }

  if (!canManage) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Only workspace owners and admins can use the demo toolkit.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Demo Toolkit</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Test credits, borrowing, routing, and provider failures without real API spend.
        </p>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
        {settingsLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : settings ? (
          <>
            <Section
              title="Pricing Profile"
              description="Controls how many credits each provider consumes. Demo charges all providers including Ollama."
            >
              <div className="flex flex-wrap gap-2">
                {(["production", "demo", "free"] as PricingProfileType[]).map((profile) => (
                  <Button
                    key={profile}
                    size="sm"
                    variant={settings.pricing_profile === profile ? "default" : "outline"}
                    onClick={() => settingsMutation.mutate({ pricing_profile: profile })}
                    disabled={settingsMutation.isPending}
                  >
                    {profile}
                  </Button>
                ))}
              </div>
            </Section>

            <Section
              title="Workspace Credits"
              description="Adjust member balances through ledger reconciliation (never direct balance mutation)."
            >
              {budgetsLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : (
                <div className="space-y-3">
                  {budgets.map((budget) => {
                    const member = members.find((item) => item.user_id === budget.user_id);
                    return (
                      <div
                        key={budget.user_id}
                        className="flex flex-wrap items-end gap-3 rounded-md border border-[var(--color-border)] p-3"
                      >
                        <div className="min-w-[10rem] flex-1">
                          <p className="text-sm font-medium">{member?.name ?? budget.user_id}</p>
                          <p className="text-xs text-[var(--color-muted-foreground)]">
                            Remaining: {formatCredits(budget.remaining_credits)}
                          </p>
                        </div>
                        <form
                          className="flex items-end gap-2"
                          onSubmit={(event) => {
                            event.preventDefault();
                            const form = event.currentTarget;
                            const input = form.elements.namedItem("remaining") as HTMLInputElement;
                            creditMutation.mutate({
                              userId: budget.user_id,
                              remaining: input.value,
                            });
                          }}
                        >
                          <div>
                            <Label htmlFor={`remaining-${budget.user_id}`} className="text-xs">
                              Set remaining
                            </Label>
                            <Input
                              id={`remaining-${budget.user_id}`}
                              name="remaining"
                              type="number"
                              min="0"
                              step="0.01"
                              defaultValue={budget.remaining_credits}
                              className="mt-1 w-28"
                            />
                          </div>
                          <Button type="submit" size="sm" disabled={creditMutation.isPending}>
                            Apply
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => resetUserMutation.mutate(budget.user_id)}
                            disabled={resetUserMutation.isPending}
                          >
                            Reset
                          </Button>
                        </form>
                      </div>
                    );
                  })}
                </div>
              )}
            </Section>

            <Section
              title="Quick Actions"
              description="Bulk credit and ledger operations for demo workspaces."
            >
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => actionMutation.mutate("reset-all")}
                  disabled={actionMutation.isPending}
                >
                  Reset all credits
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => actionMutation.mutate("clear-ledger")}
                  disabled={actionMutation.isPending}
                >
                  Clear ledger history
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => actionMutation.mutate("reseed")}
                  disabled={actionMutation.isPending}
                >
                  Reseed demo allocations
                </Button>
              </div>
            </Section>

            <Section
              title="Provider Simulation"
              description="Failures are injected before external APIs so gateway refunds and borrow release run naturally."
            >
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    "normal",
                    "timeout",
                    "unauthorized",
                    "rate_limit",
                    "server_error",
                  ] as ProviderSimulationMode[]
                ).map((mode) => (
                  <Button
                    key={mode}
                    size="sm"
                    variant={settings.provider_simulation === mode ? "default" : "outline"}
                    onClick={() => settingsMutation.mutate({ provider_simulation: mode })}
                    disabled={settingsMutation.isPending}
                  >
                    {mode}
                  </Button>
                ))}
              </div>
            </Section>

            <Section
              title="Routing Override"
              description="Temporarily bypass routing policy for predictable account selection."
            >
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    "normal",
                    "first_account",
                    "second_account",
                    "random",
                    "specific_account",
                  ] as RoutingOverrideMode[]
                ).map((mode) => (
                  <Button
                    key={mode}
                    size="sm"
                    variant={settings.routing_override_mode === mode ? "default" : "outline"}
                    onClick={() =>
                      settingsMutation.mutate({
                        routing_override_mode: mode,
                        routing_override_account_id:
                          mode === "specific_account"
                            ? settings.routing_override_account_id ?? accounts[0]?.id ?? null
                            : null,
                      })
                    }
                    disabled={settingsMutation.isPending}
                  >
                    {mode.replaceAll("_", " ")}
                  </Button>
                ))}
              </div>
              {settings.routing_override_mode === "specific_account" && accounts.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {accounts.map((account) => (
                    <Button
                      key={account.id}
                      size="sm"
                      variant={
                        settings.routing_override_account_id === account.id ? "default" : "outline"
                      }
                      onClick={() =>
                        settingsMutation.mutate({
                          routing_override_mode: "specific_account",
                          routing_override_account_id: account.id,
                        })
                      }
                    >
                      {account.display_name}
                    </Button>
                  ))}
                </div>
              ) : null}
            </Section>

            <Section title="Recent Demo Events" description="Audit trail of demo toolkit actions.">
              {eventsLoading ? (
                <Skeleton className="h-24 w-full" />
              ) : events.length === 0 ? (
                <p className="text-sm text-[var(--color-muted-foreground)]">No demo events yet.</p>
              ) : (
                <ul className="space-y-2">
                  {events.map((event) => (
                    <li
                      key={event.id}
                      className="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{event.event_type}</span>
                        <span className="text-xs text-[var(--color-muted-foreground)]">
                          {new Date(event.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="mt-1 text-[var(--color-muted-foreground)]">{event.message}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </>
        ) : null}
      </div>
    </div>
  );
}
