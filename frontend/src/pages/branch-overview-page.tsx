import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, GitBranch, GitGraph, Network } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { BranchTreeNode } from "@/types/api";

function BranchNode({ node, depth = 0 }: { node: BranchTreeNode; depth?: number }) {
  return (
    <div className="space-y-2">
      <Link
        to={`/c/${node.id}`}
        className="flex items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3 transition-colors hover:bg-[var(--color-accent)]"
        style={{ marginLeft: depth * 16 }}
      >
        <GitBranch className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-muted-foreground)]" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium">{node.branch_name || node.title}</p>
            {depth === 0 ? (
              <span className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                Root
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">
            Owner {node.owner_name ?? "Unknown"} · {node.commit_count} commits ·{" "}
            {node.message_count} messages · {node.participant_count} participants · Active{" "}
            {formatTimestamp(node.latest_activity_at)}
          </p>
          {node.parent_conversation_id ? (
            <p className="mt-1 text-[11px] text-[var(--color-muted-foreground)]">
              {node.commits_ahead} ahead · {node.commits_behind} behind
              {node.common_ancestor_commit_hash
                ? ` · LCA ${node.common_ancestor_commit_hash}`
                : ""}
            </p>
          ) : null}
        </div>
      </Link>
      {node.children.map((child) => (
        <BranchNode key={child.id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export function BranchOverviewPage() {
  const { conversationId } = useParams();

  const { data: tree, isLoading, isError } = useQuery({
    queryKey: ["branch-tree", conversationId],
    queryFn: () => conversationApi.getBranchTree(conversationId!),
    enabled: Boolean(conversationId),
  });

  const { data: overview } = useQuery({
    queryKey: ["family-overview", conversationId],
    queryFn: () => conversationApi.getFamilyOverview(conversationId!),
    enabled: Boolean(conversationId),
  });

  if (!conversationId) {
    return null;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col px-6 py-6">
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to={`/c/${conversationId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold">Branch Overview</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Family hierarchy, status, and aggregate activity.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to={`/c/${conversationId}/branches`}>
            <Network className="mr-2 h-4 w-4" />
            Branch manager
          </Link>
        </Button>
        <Button asChild variant="outline" size="sm">
          <Link to={`/c/${conversationId}/graph`}>
            <GitGraph className="mr-2 h-4 w-4" />
            Commit graph
          </Link>
        </Button>
      </div>

      {overview ? (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Total commits", overview.total_commits],
            ["Total branches", overview.total_branches],
            ["Total participants", overview.total_participants],
            ["Total messages", overview.total_messages],
            ["AI requests", overview.ai_request_count],
            ["Credits consumed", overview.credits_used],
            [
              "Latest activity",
              overview.latest_activity ? formatTimestamp(overview.latest_activity) : "—",
            ],
            [
              "Providers used",
              overview.providers_used.length ? overview.providers_used.join(", ") : "None",
            ],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3"
            >
              <p className="text-[11px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                {label}
              </p>
              <p className="mt-1 text-sm font-semibold">{value}</p>
            </div>
          ))}
        </div>
      ) : null}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : isError || !tree ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">Unable to load branch tree.</p>
      ) : (
        <BranchNode node={tree.root} />
      )}
    </div>
  );
}
