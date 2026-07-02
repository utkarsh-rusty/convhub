import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, Pencil } from "lucide-react";
import { NavLink, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { RenameConversationDialog } from "@/components/conversation/rename-conversation-dialog";
import { ParticipantAvatarStack } from "@/components/conversation/participant-avatar-stack";
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

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
          Conversations
        </p>
        <Button
          variant="ghost"
          size="icon"
          aria-label="New conversation"
          disabled={!activeWorkspaceId || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          <MessageSquarePlus className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 px-2 pb-4">
        {isLoading ? (
          <div className="space-y-2 px-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <div className="px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
            Could not load conversations. Check your connection and try again.
          </div>
        ) : conversations.length === 0 ? (
          <div className="px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
            No conversations yet. Create one to start chatting.
          </div>
        ) : (
          <div className="space-y-1">
            {conversations.map((conversation) => (
              <ConversationSidebarItem
                key={conversation.id}
                conversation={conversation}
                active={conversation.id === conversationId}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

function ConversationSidebarItem({
  conversation,
  active,
}: {
  conversation: ConversationResponse;
  active: boolean;
}) {
  const [renameOpen, setRenameOpen] = useState(false);

  return (
    <>
      <div
        className={cn(
          "group flex items-center gap-1 rounded-md px-2 py-1.5",
          active && "bg-[var(--color-accent)]",
        )}
      >
        <NavLink
          to={`/c/${conversation.id}`}
          className="flex min-w-0 flex-1 items-center gap-2 truncate text-sm hover:text-[var(--color-foreground)]"
        >
          <ParticipantAvatarStack
            participants={conversation.participants}
            max={2}
            className="shrink-0"
          />
          <span className="truncate">{conversation.title}</span>
        </NavLink>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 opacity-0 group-hover:opacity-100"
          aria-label="Rename conversation"
          onClick={() => setRenameOpen(true)}
        >
          <Pencil className="h-3.5 w-3.5" />
        </Button>
      </div>

      <RenameConversationDialog
        conversation={conversation}
        open={renameOpen}
        onOpenChange={setRenameOpen}
      />
    </>
  );
}