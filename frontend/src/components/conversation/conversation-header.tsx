import { useQuery } from "@tanstack/react-query";

import { conversationApi } from "@/lib/api";
import { useAuth } from "@/context/auth-context";
import { InviteParticipantsDialog } from "@/components/conversation/invite-participants-dialog";
import { ParticipantAvatarStack } from "@/components/conversation/participant-avatar-stack";
import type { ConnectionStatus } from "@/types/realtime";
import type { ConversationResponse } from "@/types/api";

interface ConversationHeaderProps {
  conversation: ConversationResponse;
  connectionStatus?: ConnectionStatus;
}

export function ConversationHeader({ conversation, connectionStatus }: ConversationHeaderProps) {
  const { user } = useAuth();

  const { data: participants = [] } = useQuery({
    queryKey: ["participants", conversation.id],
    queryFn: () => conversationApi.listParticipants(conversation.id),
  });

  const isOwner = participants.some(
    (participant) => participant.user_id === user?.id && participant.role === "owner",
  );

  return (
    <div className="flex items-start justify-between gap-4 border-b border-[var(--color-border)] px-6 py-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold">{conversation.title}</h2>
          <ParticipantAvatarStack participants={conversation.participants} max={4} size="md" />
        </div>
        <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">
          {conversation.participant_count} participant
          {conversation.participant_count === 1 ? "" : "s"} · Last active{" "}
          {new Date(conversation.last_activity_at).toLocaleString()}
          {connectionStatus ? ` · Live ${connectionStatus}` : null}
        </p>
      </div>

      {isOwner && (
        <InviteParticipantsDialog
          conversationId={conversation.id}
          participantUserIds={participants.map((participant) => participant.user_id)}
        />
      )}
    </div>
  );
}
