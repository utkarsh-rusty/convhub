import type { MessageResponse } from "@/types/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn, getInitials } from "@/lib/utils";

interface MessageBubbleProps {
  message: MessageResponse;
  isOwn: boolean;
  authorName?: string;
}

export function MessageBubble({ message, isOwn, authorName }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  const displayName = isAssistant ? "Assistant" : authorName ?? "Member";

  return (
    <div className={cn("flex gap-3", isOwn ? "flex-row-reverse" : "flex-row")}>
      <Avatar className="mt-1 h-8 w-8 shrink-0">
        <AvatarFallback>
          {isAssistant ? "AI" : getInitials(authorName ?? "User")}
        </AvatarFallback>
      </Avatar>

      <div className={cn("flex max-w-[75%] flex-col gap-1", isOwn ? "items-end" : "items-start")}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-[var(--color-muted-foreground)]">
            {displayName}
          </span>
          {isAssistant && message.provider && (
            <span className="rounded-full bg-[var(--color-accent)] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide">
              {message.provider}
            </span>
          )}
          <span className="text-[10px] text-[var(--color-muted-foreground)]">
            {new Date(message.created_at).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>

        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm",
            isOwn &&
              "rounded-br-md bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
            isAssistant &&
              "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-muted)]/60",
            !isOwn &&
              !isAssistant &&
              "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-card)]",
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    </div>
  );
}
