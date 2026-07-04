import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, GitBranch, Lock, MessageSquarePlus, Pencil, RotateCcw } from "lucide-react";
import { NavLink, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, showApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { RenameConversationDialog } from "@/components/conversation/rename-conversation-dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ConversationResponse } from "@/types/api";

export function ConversationSidebar() {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const { data: conversations = [], isLoading, isError } = useQuery({
    queryKey: ["conversations", activeWorkspaceId],
    queryFn: conversationApi.list,
    enabled: Boolean(activeWorkspaceId),
    refetchOnWindowFocus: true,
  });

  const createMutation = useMutation({
    mutationFn: () => conversationApi.create(),
    onSuccess: (conversation) => {
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      navigate(`/c/${conversation.id}`);
      toast.success("Conversation created");
    },
    onError: (error) => showApiError(error, "Unable to create conversation"),
  });

  const conversationTree = useMemo(
    () => buildConversationTree(conversations),
    [conversations],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between px-3 py-2.5">
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
          Conversations
        </p>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="New conversation"
          disabled={!activeWorkspaceId || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 px-1.5 pb-3">
        {isLoading ? (
          <div className="space-y-2 px-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <div className="px-3 py-6 text-xs text-[var(--color-muted-foreground)]">
            Could not load conversations.
          </div>
        ) : conversations.length === 0 ? (
          <div className="px-3 py-6 text-xs text-[var(--color-muted-foreground)]">
            No conversations yet.
          </div>
        ) : (
          <div className="space-y-0.5">
            {conversationTree.map((node) => (
              <ConversationTreeNodeView
                key={node.conversation.id}
                node={node}
                activeId={conversationId}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

interface ConversationTreeNode {
  conversation: ConversationResponse;
  children: ConversationTreeNode[];
}

export function buildConversationTree(
  conversations: ConversationResponse[],
): ConversationTreeNode[] {
  const byId = new Map(
    conversations.map((conversation) => [
      conversation.id,
      { conversation, children: [] as ConversationTreeNode[] },
    ]),
  );
  const roots: ConversationTreeNode[] = [];

  for (const conversation of conversations) {
    const node = byId.get(conversation.id)!;
    const parentId = conversation.parent_conversation_id ?? null;
    if (parentId && byId.has(parentId)) {
      byId.get(parentId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function ConversationTreeNodeView({
  node,
  activeId,
  depth = 0,
}: {
  node: ConversationTreeNode;
  activeId?: string;
  depth?: number;
}) {
  const hasChildren = node.children.length > 0;
  const containsActive =
    node.conversation.id === activeId ||
    node.children.some((child) => containsConversation(child, activeId));
  const [expanded, setExpanded] = useState(containsActive || depth === 0);

  return (
    <div>
      <div className="flex items-start gap-0.5">
        {hasChildren ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="mt-0.5 h-6 w-6 shrink-0 transition-colors duration-150"
            aria-label={expanded ? "Collapse branch" : "Expand branch"}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? (
              <ChevronDown className="h-3 w-3 transition-transform duration-150" />
            ) : (
              <ChevronRight className="h-3 w-3 transition-transform duration-150" />
            )}
          </Button>
        ) : (
          <span className="inline-block h-6 w-6 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <ConversationSidebarItem
            conversation={node.conversation}
            active={node.conversation.id === activeId}
            isBranch={depth > 0}
          />
        </div>
      </div>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200 ease-out",
          hasChildren && expanded ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        {hasChildren ? (
          <div className="ml-3 space-y-0.5 border-l border-[var(--color-border)] pl-1">
            {node.children.map((child) => (
              <ConversationTreeNodeView
                key={child.conversation.id}
                node={child}
                activeId={activeId}
                depth={depth + 1}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function containsConversation(node: ConversationTreeNode, activeId?: string): boolean {
  if (!activeId) {
    return false;
  }
  if (node.conversation.id === activeId) {
    return true;
  }
  return node.children.some((child) => containsConversation(child, activeId));
}

function ConversationSidebarItem({
  conversation,
  active,
  isBranch = false,
}: {
  conversation: ConversationResponse;
  active: boolean;
  isBranch?: boolean;
}) {
  const { user } = useAuth();
  const [renameOpen, setRenameOpen] = useState(false);
  const branchLabel = conversation.branch_name?.trim();
  const isOwner = conversation.owner_id === user?.id;
  const isReadOnly = !conversation.is_participant;
  const commitCount = conversation.commit_count ?? 0;
  const activity = conversation.latest_activity_at ?? conversation.last_activity_at;

  return (
    <>
      <div
        className={cn(
          "group flex items-start gap-1 rounded-md px-1.5 py-1 transition-colors duration-150",
          active && "bg-[var(--color-accent)]",
          conversation.is_restored && "border-l-2 border-sky-500/60 pl-1",
        )}
      >
        <NavLink
          to={`/c/${conversation.id}`}
          className="flex min-w-0 flex-1 items-start gap-1.5 text-sm hover:text-[var(--color-foreground)]"
        >
          <span className="mt-0.5 text-[var(--color-muted-foreground)]" aria-hidden="true">
            {conversation.is_restored ? (
              <RotateCcw className="h-3 w-3 text-sky-600 dark:text-sky-400" />
            ) : isBranch ? (
              <GitBranch className="h-3 w-3" />
            ) : (
              <span className="inline-block h-3 w-3 text-center text-[10px]">●</span>
            )}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="block truncate text-[13px] font-medium leading-tight">
                {branchLabel || conversation.title}
              </span>
              {conversation.is_restored ? (
                <span className="shrink-0 rounded-full bg-sky-500/10 px-1 py-px text-[9px] font-medium uppercase tracking-wide text-sky-700 dark:text-sky-300">
                  Restored
                </span>
              ) : null}
            </span>
            <span className="mt-0.5 flex items-center gap-1.5 text-[10px] leading-tight text-[var(--color-muted-foreground)]">
              <span>
                {commitCount} commit{commitCount === 1 ? "" : "s"}
              </span>
              <span aria-hidden="true">·</span>
              <span className="truncate">{formatTimestamp(activity)}</span>
              {isReadOnly ? (
                <Lock className="h-2.5 w-2.5 shrink-0" aria-label="Read-only" />
              ) : null}
            </span>
          </span>
        </NavLink>
        {isOwner ? (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 transition-opacity duration-150 group-hover:opacity-100"
            aria-label="Rename conversation"
            onClick={() => setRenameOpen(true)}
          >
            <Pencil className="h-3 w-3" />
          </Button>
        ) : null}
      </div>

      {isOwner ? (
        <RenameConversationDialog
          conversation={conversation}
          open={renameOpen}
          onOpenChange={setRenameOpen}
        />
      ) : null}
    </>
  );
}
