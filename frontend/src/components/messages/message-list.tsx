import type { MessageResponse } from "@/types/api";
import { cn } from "@/lib/utils";

interface MessageListProps {
  messages: MessageResponse[];
  currentUserId?: string;
}

export function MessageList({ messages, currentUserId }: MessageListProps) {
  if (!messages.length) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        No messages yet. Send the first message below.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} isOwn={message.author_id === currentUserId} />
      ))}
    </div>
  );
}

function MessageBubble({ message, isOwn }: { message: MessageResponse; isOwn: boolean }) {
  const isAssistant = message.role === "assistant";

  return (
    <div className={cn("flex", isOwn ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-6",
          isOwn && "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
          isAssistant && "bg-[var(--color-muted)] text-[var(--color-foreground)]",
          !isOwn && !isAssistant && "bg-[var(--color-accent)] text-[var(--color-foreground)]",
        )}
      >
        <p className="mb-1 text-[10px] uppercase tracking-wide opacity-70">{message.role}</p>
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
