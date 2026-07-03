import { GitBranch } from "lucide-react";

import { formatExecutionBadge, formatRoutingPolicy, formatTimestamp } from "@/lib/format";
import type { ExecutionSummary, MessageResponse } from "@/types/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn, getInitials } from "@/lib/utils";

interface MessageBubbleProps {
  message: MessageResponse;
  isOwn: boolean;
  authorName?: string;
  onBranch?: (messageId: string) => void;
  highlighted?: boolean;
  highlightQuery?: string;
}

function ExecutionBadge({ execution }: { execution: ExecutionSummary }) {
  const providerLabel =
    execution.provider.charAt(0).toUpperCase() + execution.provider.slice(1);
  const tooltip = `${formatExecutionBadge(execution)} · ${formatRoutingPolicy(execution.routing_policy)}`;
  const isBorrowed = execution.execution_type === "borrowed_provider";

  return (
    <span className="inline-flex flex-wrap items-center gap-1" title={tooltip}>
      <span className="inline-flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-background)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-muted-foreground)]">
        {providerLabel}
      </span>
      {isBorrowed ? (
        <span className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">
          Borrowed
        </span>
      ) : null}
    </span>
  );
}

function renderHighlightedContent(content: string, query?: string) {
  if (!query?.trim()) {
    return content;
  }
  const needle = query.trim();
  const lowerContent = content.toLowerCase();
  const lowerNeedle = needle.toLowerCase();
  const parts: Array<string | { match: string }> = [];
  let cursor = 0;
  while (cursor < content.length) {
    const index = lowerContent.indexOf(lowerNeedle, cursor);
    if (index === -1) {
      parts.push(content.slice(cursor));
      break;
    }
    if (index > cursor) {
      parts.push(content.slice(cursor, index));
    }
    parts.push({ match: content.slice(index, index + needle.length) });
    cursor = index + needle.length;
  }
  return parts.map((part, index) =>
    typeof part === "string" ? (
      <span key={index}>{part}</span>
    ) : (
      <mark key={index} className="rounded bg-yellow-300/60 px-0.5 text-inherit">
        {part.match}
      </mark>
    ),
  );
}

export function MessageBubble({
  message,
  isOwn,
  authorName,
  onBranch,
  highlighted = false,
  highlightQuery,
}: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  const displayName = isAssistant ? "Assistant" : authorName ?? "Member";

  return (
    <div
      id={`message-${message.id}`}
      className={cn(
        "group flex gap-3 scroll-mt-24",
        isOwn ? "flex-row-reverse" : "flex-row",
        highlighted && "rounded-xl ring-2 ring-yellow-400/70",
      )}
    >
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

      <div className={cn("flex max-w-[80%] flex-col gap-1", isOwn ? "items-end" : "items-start")}>
        <div className={cn("flex flex-wrap items-center gap-2", isOwn && "flex-row-reverse")}>
          <span className="text-xs font-medium text-[var(--color-foreground)]">{displayName}</span>
          <span className="text-[10px] text-[var(--color-muted-foreground)]">
            {formatTimestamp(message.created_at)}
          </span>
          {onBranch ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onBranch(message.id)}
              className="h-6 gap-1 px-2 text-[10px] font-medium text-[var(--color-muted-foreground)] opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
              aria-label="Branch from here"
            >
              <GitBranch className="h-3 w-3" />
              Branch from here
            </Button>
          ) : null}
        </div>

        <div
          className={cn(
            "rounded-2xl px-3.5 py-2.5 text-sm leading-6 shadow-sm",
            isOwn &&
              "rounded-br-md bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
            isAssistant &&
              "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-muted)]/50",
            !isOwn &&
              !isAssistant &&
              "rounded-bl-md border border-[var(--color-border)] bg-[var(--color-card)]",
          )}
        >
          <p className="whitespace-pre-wrap">
            {renderHighlightedContent(message.content, highlightQuery)}
          </p>
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
      <div className="max-w-[80%] rounded-2xl rounded-bl-md border border-[var(--color-border)] bg-[var(--color-muted)]/50 px-3.5 py-2.5 text-sm leading-6">
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
