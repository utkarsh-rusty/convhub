import { formatExecutionBadge, formatRoutingPolicy, formatTimestamp } from "@/lib/format";
import type { ExecutionSummary, MessageResponse } from "@/types/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn, getInitials } from "@/lib/utils";

interface MessageBubbleProps {
  message: MessageResponse;
  isOwn: boolean;
  authorName?: string;
}

function ExecutionBadge({ execution }: { execution: ExecutionSummary }) {
  const label = formatExecutionBadge(execution);
  const tooltip = `Routing Policy: ${formatRoutingPolicy(execution.routing_policy)}`;

  return (
    <span
      title={tooltip}
      className="inline-flex max-w-full items-center rounded-full border border-[var(--color-border)] bg-[var(--color-background)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-muted-foreground)]"
    >
      {label}
    </span>
  );
}

export function MessageBubble({ message, isOwn, authorName }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  const displayName = isAssistant ? "Assistant" : authorName ?? "Member";

  return (
    <div className={cn("flex gap-3", isOwn ? "flex-row-reverse" : "flex-row")}>
      <Avatar
        className={cn(
          "mt-1 h-9 w-9 shrink-0",
          isAssistant && "ring-2 ring-[var(--color-primary)]/20",
        )}
      >
        <AvatarFallback className={isAssistant ? "bg-[var(--color-primary)]/10 text-xs font-semibold" : ""}>
          {isAssistant ? "AI" : getInitials(authorName ?? "User")}
        </AvatarFallback>
      </Avatar>

      <div className={cn("flex max-w-[78%] flex-col gap-1.5", isOwn ? "items-end" : "items-start")}>
        <div className={cn("flex flex-wrap items-center gap-2", isOwn && "flex-row-reverse")}>
          <span className="text-xs font-medium text-[var(--color-foreground)]">{displayName}</span>
          <span className="text-[10px] text-[var(--color-muted-foreground)]">
            {formatTimestamp(message.created_at)}
          </span>
        </div>

        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm",
            isOwn &&
              "rounded-br-md bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
            isAssistant &&
              "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-muted)]/50",
            !isOwn &&
              !isAssistant &&
              "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-card)]",
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {isAssistant && message.execution && (
          <ExecutionBadge execution={message.execution} />
        )}
      </div>
    </div>
  );
}

export function StreamingAssistantBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-3">
      <Avatar className="mt-1 h-9 w-9 shrink-0 ring-2 ring-[var(--color-primary)]/20">
        <AvatarFallback className="bg-[var(--color-primary)]/10 text-xs font-semibold">AI</AvatarFallback>
      </Avatar>
      <div className="max-w-[78%] rounded-2xl rounded-bl-md border border-[var(--color-border)] bg-[var(--color-muted)]/50 px-4 py-3 text-sm leading-6">
        <p className="whitespace-pre-wrap">{content}</p>
      </div>
    </div>
  );
}

export function TypingIndicator({ label = "Assistant is typing" }: { label?: string }) {
  return (
    <div className="flex gap-3 px-6 py-2">
      <Avatar className="h-9 w-9 shrink-0 ring-2 ring-[var(--color-primary)]/20">
        <AvatarFallback className="bg-[var(--color-primary)]/10 text-xs font-semibold">AI</AvatarFallback>
      </Avatar>
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-md border border-[var(--color-border)] bg-[var(--color-muted)]/50 px-4 py-3">
        <span className="text-xs text-[var(--color-muted-foreground)]">{label}</span>
        <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--color-muted-foreground)] [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--color-muted-foreground)] [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--color-muted-foreground)]" />
      </div>
    </div>
  );
}
