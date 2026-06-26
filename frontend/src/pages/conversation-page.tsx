import { useQuery } from "@tanstack/react-query";
import { Navigate, useParams } from "react-router-dom";

import { conversationApi, messageApi } from "@/lib/api";
import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { MessageComposer } from "@/components/messages/message-composer";
import { MessageList } from "@/components/messages/message-list";
import { Skeleton } from "@/components/ui/skeleton";

export function ConversationPage() {
  const { conversationId } = useParams();
  const { user } = useAuth();
  const { activeWorkspaceId, workspaces, isLoading: workspacesLoading } = useWorkspace();

  const { data: conversation, isLoading: conversationLoading } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => conversationApi.get(conversationId!),
    enabled: Boolean(conversationId && activeWorkspaceId),
  });

  const { data: messages = [], isLoading: messagesLoading } = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => messageApi.list(conversationId!),
    enabled: Boolean(conversationId && activeWorkspaceId),
  });

  if (!workspacesLoading && workspaces.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-muted-foreground)]">
        Create a workspace to start using conversations.
      </div>
    );
  }

  if (!conversationId) {
    return <Navigate to="/" replace />;
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
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">{conversation.title}</h2>
        <p className="text-xs text-[var(--color-muted-foreground)]">
          Last active {new Date(conversation.last_activity_at).toLocaleString()}
        </p>
      </div>

      <MessageList messages={messages} currentUserId={user?.id} />
      <MessageComposer conversationId={conversation.id} />
    </div>
  );
}
