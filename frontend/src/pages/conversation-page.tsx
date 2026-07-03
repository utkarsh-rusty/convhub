import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";

import { conversationApi, messageApi, workspaceApi } from "@/lib/api";
import { APP_HOME } from "@/lib/site";
import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { useSocket } from "@/context/socket-context";
import { useConversationRealtime } from "@/hooks/use-conversation-realtime";
import { BranchConversationDialog } from "@/components/conversation/branch-conversation-dialog";
import { ConversationHeader } from "@/components/conversation/conversation-header";
import { CreateCommitDialog } from "@/components/conversation/create-commit-dialog";
import { MessageComposer } from "@/components/messages/message-composer";
import { MessageList } from "@/components/messages/message-list";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function ConversationPage() {
  const { conversationId } = useParams();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const { activeWorkspaceId, workspaces, isLoading: workspacesLoading } = useWorkspace();
  const { status: connectionStatus } = useSocket();

  const [isAiGenerating, setIsAiGenerating] = useState(false);
  const [branchTargetMessageId, setBranchTargetMessageId] = useState<string | null>(null);
  const [commitOpen, setCommitOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [focusMessageId, setFocusMessageId] = useState<string | null>(null);
  const [activeCommitHash, setActiveCommitHash] = useState<string | null>(null);
  const searchPanelRef = useRef<HTMLDivElement>(null);

  const {
    data: conversation,
    isLoading: conversationLoading,
    isError: conversationError,
  } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => conversationApi.get(conversationId!),
    enabled: Boolean(conversationId && activeWorkspaceId),
    refetchOnWindowFocus: false,
  });

  const {
    data: initialMessages = [],
    isLoading: messagesLoading,
    isError: messagesError,
  } = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => messageApi.list(conversationId!),
    enabled: Boolean(conversationId && activeWorkspaceId),
    refetchOnWindowFocus: false,
  });

  const { messages, streamingContent, typingLabel, isStreaming } = useConversationRealtime(
    conversationId,
    initialMessages,
  );

  const { data: members = [] } = useQuery({
    queryKey: ["workspace-members", activeWorkspaceId],
    queryFn: () => workspaceApi.listMembers(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  const { data: searchResults } = useQuery({
    queryKey: ["conversation-search", conversationId, activeQuery],
    queryFn: () => conversationApi.search(conversationId!, activeQuery),
    enabled: Boolean(conversationId && activeQuery.trim()),
  });

  const { data: activeCommit } = useQuery({
    queryKey: ["commit", activeCommitHash],
    queryFn: () => conversationApi.getCommit(activeCommitHash!),
    enabled: Boolean(activeCommitHash),
  });

  const memberNames = useMemo(
    () => Object.fromEntries(members.map((member) => [member.user_id, member.name])),
    [members],
  );

  const latestExecution = useMemo(() => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.role === "assistant" && message.execution) {
        return message.execution;
      }
    }
    return null;
  }, [messages]);

  const latestMessageId = messages.length > 0 ? messages[messages.length - 1].id : null;

  const highlightedMessageIds = useMemo(() => {
    const ids = new Set((searchResults?.matches ?? []).map((match) => match.message.id));
    if (focusMessageId) {
      ids.add(focusMessageId);
    }
    return ids;
  }, [searchResults, focusMessageId]);

  useEffect(() => {
    const messageId = searchParams.get("message");
    const commitHash = searchParams.get("commit");
    if (messageId) {
      setFocusMessageId(messageId);
    }
    if (commitHash) {
      setActiveCommitHash(commitHash);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!searchOpen) {
      return;
    }
    const onPointerDown = (event: MouseEvent) => {
      if (!searchPanelRef.current?.contains(event.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [searchOpen]);

  if (!workspacesLoading && workspaces.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-muted-foreground)]">
        Create a workspace to start using conversations.
      </div>
    );
  }

  if (!conversationId) {
    return <Navigate to={APP_HOME} replace />;
  }

  if (conversationError || messagesError) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-muted-foreground)]">
        Unable to load this conversation. Try refreshing or switching workspace.
      </div>
    );
  }

  if (conversationLoading || messagesLoading) {
    return (
      <div className="flex flex-1 flex-col gap-4 px-6 py-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full max-w-2xl" />
        <Skeleton className="h-24 w-full max-w-xl" />
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Conversation not found in this workspace.
      </div>
    );
  }

  const isParticipant = conversation.is_participant;
  const readOnly = !isParticipant;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={searchPanelRef}>
        <ConversationHeader
          conversation={conversation}
          connectionStatus={connectionStatus}
          latestExecution={latestExecution}
          readOnly={readOnly}
          canCommit={isParticipant && Boolean(latestMessageId)}
          onCommit={() => setCommitOpen(true)}
          searchOpen={searchOpen}
          onSearchOpenChange={setSearchOpen}
          searchInput={searchInput}
          onSearchInputChange={setSearchInput}
          onSearchSubmit={() => {
            setActiveQuery(searchInput.trim());
            setFocusMessageId(null);
          }}
        />
      </div>

      {activeCommit ? (
        <div className="shrink-0 border-b border-[var(--color-border)] bg-[var(--color-muted)]/20 px-4 py-2 text-xs sm:px-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono font-semibold">{activeCommit.commit_hash}</span>
            <span className="font-medium">{activeCommit.title}</span>
            <span className="text-[var(--color-muted-foreground)]">
              by {activeCommit.created_by_name}
            </span>
          </div>
        </div>
      ) : null}

      {activeQuery && searchResults ? (
        <div className="shrink-0 border-b border-[var(--color-border)] px-4 py-1.5 text-[11px] text-[var(--color-muted-foreground)] sm:px-5">
          <div className="flex flex-wrap items-center gap-2">
            <span>
              {searchResults.matches.length} message
              {searchResults.matches.length === 1 ? "" : "s"}
            </span>
            {searchResults.matches.slice(0, 3).map((match) => (
              <Button
                key={match.message.id}
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-[11px]"
                onClick={() => setFocusMessageId(match.message.id)}
              >
                Jump
              </Button>
            ))}
            {searchResults.commit_matches.map((match) => (
              <Button
                key={match.commit_hash}
                asChild
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-[11px]"
              >
                <Link
                  to={`/c/${conversationId}?message=${match.latest_message_id}&commit=${match.commit_hash}`}
                >
                  {match.title}
                </Link>
              </Button>
            ))}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-[11px]"
              onClick={() => {
                setActiveQuery("");
                setSearchInput("");
                setSearchOpen(false);
              }}
            >
              Clear
            </Button>
          </div>
        </div>
      ) : null}

      <MessageList
        conversationId={conversation.id}
        messages={messages}
        currentUserId={user?.id}
        memberNames={memberNames}
        isAiGenerating={isAiGenerating || isStreaming}
        streamingContent={streamingContent}
        typingLabel={typingLabel}
        onBranch={isParticipant ? setBranchTargetMessageId : undefined}
        highlightedMessageIds={highlightedMessageIds}
        highlightQuery={activeQuery}
        focusMessageId={focusMessageId}
      />
      {readOnly ? (
        <div className="shrink-0 border-t border-[var(--color-border)] px-4 py-3 text-sm text-[var(--color-muted-foreground)] sm:px-5">
          You are viewing this branch. Ask the owner to invite you to participate.
        </div>
      ) : (
        <MessageComposer
          conversationId={conversation.id}
          onGeneratingChange={setIsAiGenerating}
        />
      )}
      {branchTargetMessageId ? (
        <BranchConversationDialog
          conversationId={conversation.id}
          messageId={branchTargetMessageId}
          open={Boolean(branchTargetMessageId)}
          onOpenChange={(open) => {
            if (!open) {
              setBranchTargetMessageId(null);
            }
          }}
        />
      ) : null}
      {latestMessageId ? (
        <CreateCommitDialog
          conversationId={conversation.id}
          latestMessageId={latestMessageId}
          open={commitOpen}
          onOpenChange={setCommitOpen}
        />
      ) : null}
    </div>
  );
}
