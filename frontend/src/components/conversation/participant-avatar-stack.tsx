import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn, getInitials } from "@/lib/utils";
import type { ConversationParticipantSummary } from "@/types/api";

interface ParticipantAvatarStackProps {
  participants: ConversationParticipantSummary[];
  max?: number;
  size?: "sm" | "md";
  className?: string;
}

export function ParticipantAvatarStack({
  participants,
  max = 3,
  size = "sm",
  className,
}: ParticipantAvatarStackProps) {
  if (!participants.length) {
    return null;
  }

  const visible = participants.slice(0, max);
  const overflow = participants.length - visible.length;
  const sizeClass = size === "sm" ? "h-6 w-6 text-[10px]" : "h-8 w-8 text-xs";

  return (
    <div className={cn("flex items-center", className)}>
      {visible.map((participant, index) => (
        <Avatar
          key={participant.user_id}
          className={cn(
            sizeClass,
            "border-2 border-[var(--color-card)]",
            index > 0 && "-ml-2",
          )}
          title={participant.name}
        >
          <AvatarFallback>{getInitials(participant.name)}</AvatarFallback>
        </Avatar>
      ))}
      {overflow > 0 && (
        <span className="ml-2 text-xs text-[var(--color-muted-foreground)]">+{overflow}</span>
      )}
    </div>
  );
}
