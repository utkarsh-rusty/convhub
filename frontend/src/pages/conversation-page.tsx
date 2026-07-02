import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useParams } from "react-router-dom";

import { conversationApi, messageApi, workspaceApi } from "@/lib/api";
import { APP_HOME } from "@/lib/site";
import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { useSocket } from "@/context/socket-context";
import { useConversationRealtime } from "@/hooks/use-conversation-realtime";
import { ConversationHeader } from "@/components/conversation/conversation-header";
import { MessageComposer } from "@/components/messages/message-composer";
import { MessageList } from "@/components/messages/message-list";
import { Skeleton } from "@/components/ui/skeleton";

export function ConversationPage() {
  const { conversationId } = useParams();
  const { user } = useAuth();
  const { activeWorkspaceId, workspaces, isLoading: workspacesLoading } = useWorkspace();
  const { status: connectionStatus } = useSocket();

  const [isAiGenerating, setIsAiGenerating] = useState(false);

  const { data: conversation, isLoading: conversationLoading } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => conversationApi.get(conversationId!),
    enabled: Boolean(conversationId && activeWorkspaceId),
    refetchOnWindowFocus: false,
  });

  const { data: initialMessages = [], isLoading: messagesLoading } = useQuery({
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

  const memberNames = useMemo(
    () => Object.fromEntries(members.map((member) => [member.user_id, member.name])),
    [members],
  );

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

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ConversationHeader conversation={conversation} connectionStatus={connectionStatus} />
      <MessageList
        conversationId={conversation.id}
        messages={messages}
        currentUserId={user?.id}
        memberNames={memberNames}
        isAiGenerating={isAiGenerating || isStreaming}
        streamingContent={streamingContent}
        typingLabel={typingLabel}
      />
      <MessageComposer
        conversationId={conversation.id}
        onGeneratingChange={setIsAiGenerating}
      />
    </div>
  );
}
