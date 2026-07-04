import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  ChevronRight,
  GitBranch,
  GitCommit,
  GitCompare,
  History,
  Link2,
  MoreHorizontal,
  Search,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useAuth } from "@/context/auth-context";
import { InviteParticipantsDialog } from "@/components/conversation/invite-participants-dialog";
import { ParticipantAvatarStack } from "@/components/conversation/participant-avatar-stack";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/types/realtime";
import type { ConversationLineageResponse, ConversationResponse, ExecutionSummary } from "@/types/api";

interface ConversationHeaderProps {
  conversation: ConversationResponse;
  connectionStatus?: ConnectionStatus;
  latestExecution?: ExecutionSummary | null;
  readOnly?: boolean;
  canCommit?: boolean;
  onCommit?: () => void;
  searchOpen?: boolean;
  onSearchOpenChange?: (open: boolean) => void;
  searchInput?: string;
  onSearchInputChange?: (value: string) => void;
  onSearchSubmit?: () => void;
}

function lineageBreadcrumbLabel(item: {
  branch_name?: string | null;
  title: string;
  parent_conversation_id?: string | null;
}): string {
  const branchName = item.branch_name?.trim();
  if (branchName) {
    return branchName;
  }
  if (!item.parent_conversation_id) {
    return "Main";
  }
  return item.title;
}

function MetaBadge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "borrowed" | "live" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium",
        tone === "default" &&
          "border-[var(--color-border)] bg-[var(--color-muted)]/40 text-[var(--color-muted-foreground)]",
        tone === "borrowed" && "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        tone === "live" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
      )}
    >
      {children}
    </span>
  );
}

export function ConversationHeader({
  conversation,
  connectionStatus,
  latestExecution,
  readOnly = false,
  canCommit = false,
  onCommit,
  searchOpen = false,
  onSearchOpenChange,
  searchInput = "",
  onSearchInputChange,
  onSearchSubmit,
}: ConversationHeaderProps) {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const { data: participants = [] } = useQuery({
    queryKey: ["participants", conversation.id],
    queryFn: () => conversationApi.listParticipants(conversation.id),
  });

  const isBranch = Boolean(conversation.parent_conversation_id);

  const { data: lineage } = useQuery<ConversationLineageResponse>({
    queryKey: ["conversation-lineage", conversation.id],
    queryFn: () => conversationApi.getLineage(conversation.id),
    enabled: isBranch,
  });

  const isOwner = conversation.owner_id === user?.id;
  const ownerName =
    conversation.owner?.name ??
    participants.find((participant) => participant.user_id === conversation.owner_id)?.name ??
    "Owner";

  useEffect(() => {
    if (!menuOpen) {
      return;
    }
    const onPointerDown = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [menuOpen]);

  useEffect(() => {
    if (searchOpen) {
      searchRef.current?.focus();
    }
  }, [searchOpen]);

  const copyConversationLink = async () => {
    const url = `${window.location.origin}/c/${conversation.id}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Conversation link copied");
    } catch {
      toast.error("Unable to copy link");
    }
    setMenuOpen(false);
  };

  const breadcrumbItems = lineage
    ? [lineage.root, ...lineage.ancestors, lineage.current].filter(
        (item, index, array) => array.findIndex((entry) => entry.id === item.id) === index,
      )
    : [];

  const providerLabel = latestExecution
    ? latestExecution.provider.charAt(0).toUpperCase() + latestExecution.provider.slice(1)
    : null;
  const isBorrowed = latestExecution?.execution_type === "borrowed_provider";
  const isLive = connectionStatus === "connected";

  return (
    <div className="shrink-0 border-b border-[var(--color-border)] px-4 py-2.5 sm:px-5">
      {isBranch && breadcrumbItems.length > 0 ? (
        <nav
          aria-label="Conversation lineage"
          className="mb-1 flex flex-wrap items-center gap-0.5 text-[11px] text-[var(--color-muted-foreground)]"
        >
          {breadcrumbItems.map((item, index) => {
            const isLast = index === breadcrumbItems.length - 1;
            const label = lineageBreadcrumbLabel(item);
            return (
              <span key={item.id} className="flex items-center gap-0.5">
                {isLast ? (
                  <span className="font-medium text-[var(--color-foreground)]">{label}</span>
                ) : (
                  <Link to={`/c/${item.id}`} className="truncate hover:text-[var(--color-foreground)]">
                    {label}
                  </Link>
                )}
                {isLast ? null : <ChevronRight className="h-3 w-3 shrink-0 opacity-50" aria-hidden="true" />}
              </span>
            );
          })}
        </nav>
      ) : null}

      <div className="flex min-w-0 items-center gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="truncate text-base font-semibold leading-tight">{conversation.title}</h2>
            {conversation.is_restored ? (
              <span className="shrink-0 rounded-full border border-sky-500/30 bg-sky-500/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-sky-700 dark:text-sky-300">
                Restored
              </span>
            ) : null}
            {readOnly ? (
              <span className="shrink-0 rounded-full border border-[var(--color-border)] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
                Read-only
              </span>
            ) : null}
          </div>
          {conversation.is_restored && conversation.restored_from_commit_hash ? (
            <p className="mt-0.5 text-[11px] text-[var(--color-muted-foreground)]">
              Restored from Commit{" "}
              <span className="font-mono">#{conversation.restored_from_commit_hash}</span>
              {conversation.restored_from_package_id ? (
                <>
                  {" · "}
                  <Link
                    to={`/context-packages/${conversation.restored_from_package_id}`}
                    className="underline-offset-2 hover:underline"
                  >
                    View Context Package
                  </Link>
                </>
              ) : null}
            </p>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <div
            className={cn(
              "overflow-hidden transition-all duration-200 ease-out",
              searchOpen ? "w-44 opacity-100 sm:w-56" : "w-0 opacity-0",
            )}
          >
            {searchOpen ? (
              <form
                className="pr-1"
                onSubmit={(event) => {
                  event.preventDefault();
                  onSearchSubmit?.();
                }}
              >
                <Input
                  ref={searchRef}
                  value={searchInput}
                  onChange={(event) => onSearchInputChange?.(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Escape") {
                      onSearchOpenChange?.(false);
                    }
                  }}
                  placeholder="Search..."
                  className="h-8 text-xs"
                />
              </form>
            ) : null}
          </div>

          {canCommit && onCommit ? (
            <Button variant="default" size="sm" className="h-8 px-2.5 text-xs" onClick={onCommit}>
              <GitCommit className="mr-1.5 h-3.5 w-3.5" />
              Commit
            </Button>
          ) : null}
          <Button asChild variant="outline" size="sm" className="h-8 px-2.5 text-xs">
            <Link to={`/c/${conversation.id}/history`}>
              <History className="mr-1.5 h-3.5 w-3.5" />
              History
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm" className="hidden h-8 px-2.5 text-xs sm:inline-flex">
            <Link to={`/c/${conversation.id}/overview`}>
              <GitBranch className="mr-1.5 h-3.5 w-3.5" />
              Overview
            </Link>
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            aria-label="Search"
            aria-expanded={searchOpen}
            onClick={() => onSearchOpenChange?.(!searchOpen)}
          >
            <Search className="h-4 w-4" />
          </Button>

          <div className="relative" ref={menuRef}>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              aria-label="More actions"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((value) => !value)}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
            <div
              className={cn(
                "absolute right-0 top-full z-30 mt-1 w-44 origin-top-right rounded-md border border-[var(--color-border)] bg-[var(--color-card)] py-1 shadow-lg transition-all duration-150",
                menuOpen
                  ? "pointer-events-auto scale-100 opacity-100"
                  : "pointer-events-none scale-95 opacity-0",
              )}
            >
              <Link
                to={`/c/${conversation.id}/overview`}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-accent)] sm:hidden"
                onClick={() => setMenuOpen(false)}
              >
                <GitBranch className="h-3.5 w-3.5" />
                Overview
              </Link>
              <Link
                to={`/c/${conversation.id}/branches`}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-accent)]"
                onClick={() => setMenuOpen(false)}
              >
                <GitBranch className="h-3.5 w-3.5" />
                Branch manager
              </Link>
              <Link
                to={`/c/${conversation.id}/graph`}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-accent)]"
                onClick={() => setMenuOpen(false)}
              >
                <GitCompare className="h-3.5 w-3.5" />
                Commit graph
              </Link>
              <Link
                to={`/c/${conversation.id}/timeline`}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-accent)]"
                onClick={() => setMenuOpen(false)}
              >
                <History className="h-3.5 w-3.5" />
                Timeline
              </Link>
              <Link
                to={`/c/${conversation.id}/compare`}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-accent)]"
                onClick={() => setMenuOpen(false)}
              >
                <GitCompare className="h-3.5 w-3.5" />
                Compare
              </Link>
              <Link
                to={`/c/${conversation.id}/stats`}
                className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-[var(--color-accent)]"
                onClick={() => setMenuOpen(false)}
              >
                <BarChart3 className="h-3.5 w-3.5" />
                Statistics
              </Link>
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                onClick={() => void copyConversationLink()}
              >
                <Link2 className="h-3.5 w-3.5" />
                Copy link
              </button>
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                onClick={() => {
                  setMenuOpen(false);
                  onSearchOpenChange?.(true);
                }}
              >
                <Search className="h-3.5 w-3.5" />
                Search
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px] text-[var(--color-muted-foreground)]">
        <span className="truncate">Owner {ownerName}</span>
        <span aria-hidden="true">•</span>
        <span>
          {conversation.participant_count} participant
          {conversation.participant_count === 1 ? "" : "s"}
        </span>
        <span aria-hidden="true">•</span>
        <span className="truncate">Last active {formatTimestamp(conversation.last_activity_at)}</span>
        {providerLabel ? (
          <>
            <span aria-hidden="true">•</span>
            <MetaBadge>{providerLabel}</MetaBadge>
          </>
        ) : null}
        {isBorrowed ? (
          <>
            <span aria-hidden="true">•</span>
            <MetaBadge tone="borrowed">
              Borrowed{latestExecution?.borrowed_from ? ` from ${latestExecution.borrowed_from}` : ""}
            </MetaBadge>
          </>
        ) : null}
        {isLive ? (
          <>
            <span aria-hidden="true">•</span>
            <MetaBadge tone="live">Live</MetaBadge>
          </>
        ) : null}
      </div>

      <div className="mt-1.5 flex items-center gap-2">
        <ParticipantAvatarStack
          participants={conversation.participants}
          max={5}
          size="sm"
          ownerId={conversation.owner_id}
          showInvite={isOwner}
          onInvite={() => setInviteOpen(true)}
        />
      </div>

      {isOwner ? (
        <InviteParticipantsDialog
          conversationId={conversation.id}
          participantUserIds={participants.map((participant) => participant.user_id)}
          open={inviteOpen}
          onOpenChange={setInviteOpen}
          hideTrigger
        />
      ) : null}
    </div>
  );
}
