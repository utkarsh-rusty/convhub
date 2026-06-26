import type { MessageResponse } from "@/types/api";
import { MessageBubble } from "@/components/messages/message-bubble";

interface MessageListProps {
  messages: MessageResponse[];
  currentUserId?: string;
  memberNames?: Record<string, string>;
}

export function MessageList({ messages, currentUserId, memberNames = {} }: MessageListProps) {
  if (!messages.length) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        No messages yet. Send the first message or ask AI below.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-5 overflow-y-auto px-6 py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          isOwn={message.author_id === currentUserId}
          authorName={
            message.author_id ? memberNames[message.author_id] ?? "Member" : undefined
          }
        />
      ))}
    </div>
  );
}
