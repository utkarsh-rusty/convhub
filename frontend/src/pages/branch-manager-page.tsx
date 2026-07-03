import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, GitBranch, GitGraph } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { BranchTreeNode } from "@/types/api";

type BranchFilter = "all" | "active" | "archived" | "mine" | "owned" | "recent";

function filterNode(node: BranchTreeNode, filter: BranchFilter, now: number): BranchTreeNode | null {
  const children = node.children
    .map((child) => filterNode(child, filter, now))
    .filter((child): child is BranchTreeNode => child !== null);

  const isArchived = Boolean(node.archived_at);
  const recent =
    now - new Date(node.latest_activity_at).getTime() < 1000 * 60 * 60 * 24 * 7;
  const matches =
    filter === "all" ||
    (filter === "active" && !isArchived) ||
    (filter === "archived" && isArchived) ||
    (filter === "mine" && node.is_participant) ||
    (filter === "owned" && node.is_owned_by_viewer) ||
    (filter === "recent" && recent);

  if (!matches && children.length === 0) {
    return null;
  }

  return { ...node, children };
}

function BranchManagerNode({
  node,
  depth = 0,
  onSelect,
}: {
  node: BranchTreeNode;
  depth?: number;
  onSelect: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const label = node.branch_name || node.title;

  return (
    <div>
      <button
        type="button"
        onClick={() => onSelect(node.id)}
        className="flex w-full items-start gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-accent)]"
        style={{ marginLeft: depth * 18 }}
      >
        {node.children.length > 0 ? (
          <span
            className="mt-0.5 text-[var(--color-muted-foreground)]"
            onClick={(event) => {
              event.stopPropagation();
              setExpanded((value) => !value);
            }}
          >
            {expanded ? "▾" : "▸"}
          </span>
        ) : (
          <span className="mt-0.5 text-[var(--color-muted-foreground)]">├</span>
        )}
        <GitBranch className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-muted-foreground)]" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-medium">{label}</p>
            {depth === 0 ? (
              <span className="rounded-full border border-[var(--color-border)] px-1.5 py-0.5 text-[10px] uppercase text-[var(--color-muted-foreground)]">
                Main
              </span>
            ) : null}
            {node.archived_at ? (
              <span className="rounded-full border border-[var(--color-border)] px-1.5 py-0.5 text-[10px] text-[var(--color-muted-foreground)]">
                Archived
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-[11px] text-[var(--color-muted-foreground)]">
            Owner {node.owner_name ?? "Unknown"} · {node.commit_count} commits ·{" "}
            {node.participant_count} participants · Active{" "}
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
      </button>
      {expanded
        ? node.children.map((child) => (
            <div key={child.id} className="mt-2">
              <BranchManagerNode node={child} depth={depth + 1} onSelect={onSelect} />
            </div>
          ))
        : null}
    </div>
  );
}

export function BranchManagerPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<BranchFilter>("all");
  const [query, setQuery] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["branch-manager", conversationId],
    queryFn: () => conversationApi.getBranchManager(conversationId!),
    enabled: Boolean(conversationId),
  });

  const filteredRoot = useMemo(() => {
    if (!data) {
      return null;
    }
    const now = Date.now();
    const filtered = filterNode(data.root, filter, now);
    if (!filtered) {
      return null;
    }
    if (!query.trim()) {
      return filtered;
    }
    const needle = query.trim().toLowerCase();
    const searchFilter = (node: BranchTreeNode): BranchTreeNode | null => {
      const children = node.children
        .map((child) => searchFilter(child))
        .filter((child): child is BranchTreeNode => child !== null);
      const label = `${node.branch_name ?? ""} ${node.title} ${node.owner_name ?? ""}`.toLowerCase();
      if (!label.includes(needle) && children.length === 0) {
        return null;
      }
      return { ...node, children };
    };
    return searchFilter(filtered);
  }, [data, filter, query]);

  if (!conversationId) {
    return null;
  }

  const filters: Array<{ id: BranchFilter; label: string }> = [
    { id: "all", label: "All" },
    { id: "active", label: "Active" },
    { id: "archived", label: "Archived" },
    { id: "mine", label: "Mine" },
    { id: "owned", label: "Owned by me" },
    { id: "recent", label: "Recently updated" },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col px-4 py-4 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to={`/c/${conversationId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold">Branch Manager</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Full conversation family tree with status metadata.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to={`/c/${conversationId}/graph`}>
            <GitGraph className="mr-2 h-4 w-4" />
            Commit graph
          </Link>
        </Button>
      </div>

      {data ? (
        <div className="mb-4 grid gap-3 sm:grid-cols-4">
          {[
            ["Branches", data.total_branches],
            ["Commits", data.total_commits],
            ["Messages", data.total_messages],
            ["Participants", data.total_participants],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2"
            >
              <p className="text-[11px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                {label}
              </p>
              <p className="mt-1 text-lg font-semibold">{value}</p>
            </div>
          ))}
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {filters.map((item) => (
          <Button
            key={item.id}
            type="button"
            size="sm"
            variant={filter === item.id ? "default" : "outline"}
            className={cn("h-8 text-xs", filter === item.id && "")}
            onClick={() => setFilter(item.id)}
          >
            {item.label}
          </Button>
        ))}
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter branches..."
          className="h-8 max-w-xs text-xs"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : isError || !filteredRoot ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">
          No branches match the current filters.
        </p>
      ) : (
        <div className="space-y-2 overflow-y-auto pb-6">
          <BranchManagerNode
            node={filteredRoot}
            onSelect={(id) => navigate(`/c/${id}`)}
          />
        </div>
      )}
    </div>
  );
}
