import { useLayoutEffect, useRef } from "react";

import type { MessageResponse } from "@/types/api";
import { MessageBubble, StreamingAssistantBubble, TypingIndicator } from "@/components/messages/message-bubble";

interface MessageListProps {
  conversationId: string;
  messages: MessageResponse[];
  currentUserId?: string;
  memberNames?: Record<string, string>;
  isAiGenerating?: boolean;
  streamingContent?: string | null;
  typingLabel?: string | null;
}

export function MessageList({
  conversationId,
  messages,
  currentUserId,
  memberNames = {},
  isAiGenerating = false,
  streamingContent = null,
  typingLabel = null,
}: MessageListProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
      return;
    }
    bottomRef.current?.scrollIntoView({ block: "end" });
  };

  useLayoutEffect(() => {
    scrollToBottom();
    const frame = requestAnimationFrame(scrollToBottom);
    return () => cancelAnimationFrame(frame);
  }, [conversationId, messages, streamingContent, typingLabel, isAiGenerating]);

  if (!messages.length && !isAiGenerating && !typingLabel) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        No messages yet. Send the first message or ask AI below.
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-6 py-6"
    >
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
      <div ref={bottomRef} className="h-px shrink-0" aria-hidden="true" />
    </div>
  );
}
