import { useMemo, useState } from "react";

import { formatTimestamp } from "@/lib/format";
import type { CommitGraphNode, CommitGraphResponse } from "@/types/api";
import { cn } from "@/lib/utils";

interface CommitGraphViewProps {
  graph: CommitGraphResponse;
  onSelectCommit: (commitHash: string) => void;
  selectedHash?: string | null;
  searchQuery?: string;
}

type LayoutNode = CommitGraphNode & { x: number; y: number; lane: number };

function layoutGraph(graph: CommitGraphResponse): LayoutNode[] {
  const children = new Map<string, string[]>();
  const parents = new Map<string, string | null>();
  for (const node of graph.nodes) {
    parents.set(node.commit_hash, node.parent_commit_hash ?? null);
    if (node.parent_commit_hash) {
      const list = children.get(node.parent_commit_hash) ?? [];
      list.push(node.commit_hash);
      children.set(node.parent_commit_hash, list);
    }
  }

  // Prefer explicit edges for branch forks.
  for (const edge of graph.edges) {
    parents.set(edge.target, edge.source);
    const list = children.get(edge.source) ?? [];
    if (!list.includes(edge.target)) {
      list.push(edge.target);
      children.set(edge.source, list);
    }
  }

  const roots = graph.nodes.filter((node) => {
    const parent = parents.get(node.commit_hash);
    return !parent || !graph.nodes.some((item) => item.commit_hash === parent);
  });

  const laneByHash = new Map<string, number>();
  let nextLane = 0;
  const order: string[] = [];
  const visit = (hash: string, lane: number) => {
    if (laneByHash.has(hash)) {
      return;
    }
    laneByHash.set(hash, lane);
    order.push(hash);
    const kids = children.get(hash) ?? [];
    kids.forEach((child, index) => {
      visit(child, index === 0 ? lane : ++nextLane);
    });
  };
  roots
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .forEach((root) => visit(root.commit_hash, nextLane++));

  // Include any disconnected nodes.
  for (const node of graph.nodes) {
    if (!laneByHash.has(node.commit_hash)) {
      visit(node.commit_hash, nextLane++);
    }
  }

  const byHash = new Map(graph.nodes.map((node) => [node.commit_hash, node]));
  return order.map((hash, index) => {
    const node = byHash.get(hash)!;
    const lane = laneByHash.get(hash) ?? 0;
    return {
      ...node,
      lane,
      x: 28 + lane * 28,
      y: 28 + index * 56,
    };
  });
}

export function CommitGraphView({
  graph,
  onSelectCommit,
  selectedHash,
  searchQuery = "",
}: CommitGraphViewProps) {
  const [hoverHash, setHoverHash] = useState<string | null>(null);
  const layout = useMemo(() => layoutGraph(graph), [graph]);
  const byHash = useMemo(
    () => new Map(layout.map((node) => [node.commit_hash, node])),
    [layout],
  );

  const height = Math.max(200, layout.length * 56 + 40);
  const width = Math.max(320, (Math.max(0, ...layout.map((node) => node.lane)) + 1) * 28 + 280);
  const needle = searchQuery.trim().toLowerCase();

  if (!layout.length) {
    return (
      <p className="px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
        No commits in this conversation family yet.
      </p>
    );
  }

  return (
    <div className="relative overflow-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-card)]">
      <svg width={width} height={height} className="block min-w-full">
        {graph.edges.map((edge) => {
          const source = byHash.get(edge.source);
          const target = byHash.get(edge.target);
          if (!source || !target) {
            return null;
          }
          const path = `M ${source.x} ${source.y} C ${source.x} ${(source.y + target.y) / 2}, ${target.x} ${(source.y + target.y) / 2}, ${target.x} ${target.y}`;
          return (
            <path
              key={`${edge.source}-${edge.target}`}
              d={path}
              fill="none"
              stroke="var(--color-border)"
              strokeWidth="2"
            />
          );
        })}

        {layout.map((node) => {
          const matches =
            !needle ||
            node.title.toLowerCase().includes(needle) ||
            node.author_name.toLowerCase().includes(needle) ||
            node.providers.some((provider) => provider.toLowerCase().includes(needle));
          const active = selectedHash === node.commit_hash || hoverHash === node.commit_hash;
          return (
            <g
              key={node.commit_hash}
              className={cn("cursor-pointer", !matches && "opacity-30")}
              onClick={() => onSelectCommit(node.commit_hash)}
              onMouseEnter={() => setHoverHash(node.commit_hash)}
              onMouseLeave={() => setHoverHash(null)}
            >
              <circle
                cx={node.x}
                cy={node.y}
                r={active ? 7 : 5}
                fill={active ? "var(--color-primary)" : "var(--color-card)"}
                stroke="var(--color-primary)"
                strokeWidth="2"
              />
              <text
                x={node.x + 16}
                y={node.y - 4}
                className="fill-[var(--color-foreground)] text-[12px] font-medium"
              >
                {node.title.length > 42 ? `${node.title.slice(0, 42)}…` : node.title}
              </text>
              <text
                x={node.x + 16}
                y={node.y + 12}
                className="fill-[var(--color-muted-foreground)] text-[10px]"
              >
                {node.commit_hash} · {node.author_name} · {formatTimestamp(node.created_at)}
                {node.branch_name ? ` · ${node.branch_name}` : ""}
              </text>
            </g>
          );
        })}
      </svg>

      {layout.length > 12 ? (
        <div className="absolute bottom-3 right-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)]/95 p-2 shadow-sm">
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
            Minimap
          </p>
          <svg width={120} height={80} className="block">
            {layout.map((node) => (
              <circle
                key={`mini-${node.commit_hash}`}
                cx={8 + (node.lane / Math.max(1, Math.max(...layout.map((item) => item.lane)))) * 100}
                cy={8 + (node.y / height) * 64}
                r={selectedHash === node.commit_hash ? 3 : 2}
                fill={
                  selectedHash === node.commit_hash
                    ? "var(--color-primary)"
                    : "var(--color-muted-foreground)"
                }
              />
            ))}
          </svg>
        </div>
      ) : null}
    </div>
  );
}
