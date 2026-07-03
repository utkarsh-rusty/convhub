import { Crown, Plus } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn, getInitials } from "@/lib/utils";
import type { ConversationParticipantSummary } from "@/types/api";

interface ParticipantAvatarStackProps {
  participants: ConversationParticipantSummary[];
  max?: number;
  size?: "sm" | "md";
  className?: string;
  ownerId?: string | null;
  onInvite?: () => void;
  showInvite?: boolean;
}

export function ParticipantAvatarStack({
  participants,
  max = 3,
  size = "sm",
  className,
  ownerId,
  onInvite,
  showInvite = false,
}: ParticipantAvatarStackProps) {
  if (!participants.length && !showInvite) {
    return null;
  }

  const visible = participants.slice(0, max);
  const overflow = participants.length - visible.length;
  const sizeClass = size === "sm" ? "h-6 w-6 text-[10px]" : "h-7 w-7 text-[11px]";

  return (
    <div className={cn("flex items-center", className)}>
      {visible.map((participant, index) => {
        const isOwner = ownerId === participant.user_id;
        return (
          <div
            key={participant.user_id}
            className={cn("relative transition-transform duration-150 hover:z-10 hover:scale-110", index > 0 && "-ml-1.5")}
            title={isOwner ? `${participant.name} (owner)` : participant.name}
          >
            <Avatar className={cn(sizeClass, "border-2 border-[var(--color-card)]")}>
              <AvatarFallback>{getInitials(participant.name)}</AvatarFallback>
            </Avatar>
            {isOwner ? (
              <span className="absolute -right-0.5 -top-0.5 rounded-full bg-[var(--color-card)] p-px text-amber-500">
                <Crown className="h-2.5 w-2.5 fill-current" aria-label="Owner" />
              </span>
            ) : null}
          </div>
        );
      })}
      {overflow > 0 ? (
        <span
          className={cn(
            sizeClass,
            "-ml-1.5 inline-flex items-center justify-center rounded-full border-2 border-[var(--color-card)] bg-[var(--color-muted)] text-[10px] font-medium text-[var(--color-muted-foreground)]",
          )}
          title={`${overflow} more`}
        >
          +{overflow}
        </span>
      ) : null}
      {showInvite && onInvite ? (
        <button
          type="button"
          onClick={onInvite}
          title="Invite participant"
          aria-label="Invite participant"
          className={cn(
            sizeClass,
            "-ml-1.5 inline-flex items-center justify-center rounded-full border border-dashed border-[var(--color-border)] bg-[var(--color-background)] text-[var(--color-muted-foreground)] transition-colors duration-150 hover:border-[var(--color-foreground)] hover:text-[var(--color-foreground)]",
          )}
        >
          <Plus className="h-3 w-3" />
        </button>
      ) : null}
    </div>
  );
}
