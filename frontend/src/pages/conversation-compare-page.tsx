import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ComparisonMessage } from "@/types/api";
import { cn } from "@/lib/utils";

function MessageColumn({
  title,
  messages,
  tone,
}: {
  title: string;
  messages: ComparisonMessage[];
  tone: "shared" | "left" | "right" | "divergence";
}) {
  return (
    <div className="min-w-0 flex-1 space-y-2">
      <h3 className="text-sm font-medium">{title}</h3>
      <div className="space-y-2">
        {messages.length === 0 ? (
          <p className="rounded-lg border border-dashed border-[var(--color-border)] px-3 py-4 text-xs text-[var(--color-muted-foreground)]">
            No messages
          </p>
        ) : (
          messages.map((message) => (
            <div
              key={`${tone}-${message.id}`}
              className={cn(
                "rounded-lg border px-3 py-2 text-sm",
                tone === "shared" && "border-emerald-500/40 bg-emerald-500/10",
                tone === "left" && "border-sky-500/40 bg-sky-500/10",
                tone === "right" && "border-amber-500/40 bg-amber-500/10",
                tone === "divergence" && "border-rose-500/50 bg-rose-500/10",
              )}
            >
              <p className="text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                {message.role}
              </p>
              <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function ConversationComparePage() {
  const { conversationId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeWorkspaceId } = useWorkspace();
  const selectedRightId = searchParams.get("with") ?? "";
  const [draftRightId, setDraftRightId] = useState(selectedRightId);

  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations", activeWorkspaceId],
    queryFn: conversationApi.list,
    enabled: Boolean(activeWorkspaceId),
  });

  const compareTargets = useMemo(
    () => conversations.filter((conversation) => conversation.id !== conversationId),
    [conversations, conversationId],
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversation-compare", conversationId, selectedRightId],
    queryFn: () => conversationApi.compare(conversationId!, selectedRightId),
    enabled: Boolean(conversationId && selectedRightId),
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
          <h1 className="text-xl font-semibold">Compare Branches</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Read-only message comparison by order. No merge or AI.
          </p>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div className="min-w-[240px] flex-1 space-y-1">
          <label className="text-xs text-[var(--color-muted-foreground)]" htmlFor="compare-target">
            Compare with
          </label>
          <select
            id="compare-target"
            className="h-10 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 text-sm"
            value={draftRightId}
            onChange={(event) => setDraftRightId(event.target.value)}
          >
            <option value="">Select a conversation</option>
            {compareTargets.map((conversation) => (
              <option key={conversation.id} value={conversation.id}>
                {conversation.branch_name || conversation.title}
              </option>
            ))}
          </select>
        </div>
        <Button
          disabled={!draftRightId}
          onClick={() => setSearchParams(draftRightId ? { with: draftRightId } : {})}
        >
          Compare
        </Button>
      </div>

      {!selectedRightId ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Choose another conversation to compare against this branch.
        </p>
      ) : isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : isError || !data ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">Unable to compare conversations.</p>
      ) : (
        <div className="space-y-6 overflow-y-auto">
          <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm">
            Divergence point:{" "}
            {data.divergence_message_id
              ? `message ${data.divergence_message_id}`
              : "no shared messages"}
            {data.common_ancestor_id ? ` · common ancestor ${data.common_ancestor_id}` : null}
          </div>

          <div>
            <h2 className="mb-2 text-sm font-semibold">Shared section</h2>
            <MessageColumn title="Shared messages" messages={data.shared_messages} tone="shared" />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <MessageColumn title="Left only" messages={data.left_only} tone="left" />
            <MessageColumn title="Right only" messages={data.right_only} tone="right" />
          </div>
        </div>
      )}
    </div>
  );
}
