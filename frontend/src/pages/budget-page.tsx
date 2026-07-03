import { useQuery } from "@tanstack/react-query";

import { budgetApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Skeleton } from "@/components/ui/skeleton";

function formatCredits(value: string) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function BudgetPage() {
  const { activeWorkspaceId } = useWorkspace();

  const { data: budget, isLoading: budgetLoading } = useQuery({
    queryKey: ["budget", activeWorkspaceId],
    queryFn: () => budgetApi.getMyBudget(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["credit-history", activeWorkspaceId],
    queryFn: () => budgetApi.listHistory(activeWorkspaceId!, { limit: 20 }),
    enabled: Boolean(activeWorkspaceId),
  });

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to view your budget.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Borrowing Budget</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          This budget only limits how much shared AI you may consume from teammates. Your own AI
          providers are never blocked.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {budgetLoading ? (
          <Skeleton className="mb-6 h-32 w-full" />
        ) : budget ? (
          <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Borrowing Budget Remaining</p>
              <p className="mt-1 text-2xl font-semibold">
                {formatCredits(budget.remaining_credits)}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Own Usage</p>
              <p className="mt-1 text-2xl font-semibold">{formatCredits(budget.used_credits)}</p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Borrowed Usage</p>
              <p className="mt-1 text-2xl font-semibold">
                {formatCredits(budget.borrowed_credits)}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Shared (Lent)</p>
              <p className="mt-1 text-2xl font-semibold">{formatCredits(budget.lent_credits)}</p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Monthly Allocation</p>
              <p className="mt-1 text-2xl font-semibold">
                {formatCredits(budget.monthly_credit_limit)}
              </p>
            </div>
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Reset Date</p>
              <p className="mt-1 text-2xl font-semibold">
                {new Date(budget.reset_date).toLocaleDateString()}
              </p>
            </div>
          </div>
        ) : null}

        <div>
          <h3 className="mb-3 text-sm font-medium">Recent Transactions</h3>
          {historyLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-14 w-full" />
              ))}
            </div>
          ) : history && history.items.length > 0 ? (
            <div className="space-y-2">
              {history.items.map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="font-medium">{tx.display_description}</p>
                    <p className="truncate text-sm capitalize text-[var(--color-muted-foreground)]">
                      {tx.transaction_type}
                    </p>
                  </div>
                  <div className="ml-4 text-right">
                    <p className="font-medium">{formatCredits(tx.amount)}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      {new Date(tx.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-muted-foreground)]">No transactions yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
