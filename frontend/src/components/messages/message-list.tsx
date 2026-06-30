import type { MessageResponse } from "@/types/api";
import { MessageBubble, StreamingAssistantBubble, TypingIndicator } from "@/components/messages/message-bubble";

interface MessageListProps {
  messages: MessageResponse[];
  currentUserId?: string;
  memberNames?: Record<string, string>;
  isAiGenerating?: boolean;
  streamingContent?: string | null;
  typingLabel?: string | null;
}

export function MessageList({
  messages,
  currentUserId,
  memberNames = {},
  isAiGenerating = false,
  streamingContent = null,
  typingLabel = null,
}: MessageListProps) {
  if (!messages.length && !isAiGenerating && !typingLabel) {
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
      {streamingContent ? <StreamingAssistantBubble content={streamingContent} /> : null}
      {typingLabel ? <TypingIndicator label={typingLabel} /> : null}
      {!streamingContent && !typingLabel && isAiGenerating ? <TypingIndicator /> : null}
    </div>
  );
}
