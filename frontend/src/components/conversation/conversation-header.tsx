import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3,
  ChevronRight,
  Code2,
  GitBranch,
  GitCommit,
  GitCompare,
  History,
  Link2,
  MoreHorizontal,
  Search,
  Unlink,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, repositoryApi, showApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { InviteParticipantsDialog } from "@/components/conversation/invite-participants-dialog";
import { EnableCodingDialog } from "@/components/conversation/enable-coding-dialog";
import { AttachRepositoryDialog } from "@/components/conversation/attach-repository-dialog";
import { DisableCodingDialog } from "@/components/conversation/disable-coding-dialog";
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

function formatSyncStatus(status: string): string {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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
  const { activeWorkspaceId } = useWorkspace();
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [enableCodingOpen, setEnableCodingOpen] = useState(false);
  const [attachRepositoryOpen, setAttachRepositoryOpen] = useState(false);
  const [changeRepositoryOpen, setChangeRepositoryOpen] = useState(false);
  const [disableCodingOpen, setDisableCodingOpen] = useState(false);
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

  const { data: repositoryBranches = [] } = useQuery({
    queryKey: ["repository-branches", conversation.repository?.id],
    queryFn: () => repositoryApi.listBranches(conversation.repository!.id),
    enabled: Boolean(conversation.coding_enabled && conversation.repository?.id),
  });

  const isOwner = conversation.owner_id === user?.id;
  const hasRepository = Boolean(conversation.repository);
  const defaultRepositoryBranch = repositoryBranches.find((branch) => branch.is_default) ?? repositoryBranches[0];
  const branchMemory = defaultRepositoryBranch?.memory ?? null;

  const detachRepositoryMutation = useMutation({
    mutationFn: () => conversationApi.detachRepository(conversation.id),
    onSuccess: () => {
      toast.success("Repository detached");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
      void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["repository-branches", activeWorkspaceId] });
      setMenuOpen(false);
    },
    onError: (error) => showApiError(error, "Unable to detach repository"),
  });

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
          {!conversation.coding_enabled && isOwner ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs"
              onClick={() => setEnableCodingOpen(true)}
            >
              <Code2 className="mr-1.5 h-3.5 w-3.5" />
              Enable coding
            </Button>
          ) : null}
          {conversation.coding_enabled && !hasRepository && isOwner ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs"
              onClick={() => setAttachRepositoryOpen(true)}
            >
              <Link2 className="mr-1.5 h-3.5 w-3.5" />
              Attach repository
            </Button>
          ) : null}
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
              {isOwner && !conversation.coding_enabled ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                  onClick={() => {
                    setMenuOpen(false);
                    setEnableCodingOpen(true);
                  }}
                >
                  <Code2 className="h-3.5 w-3.5" />
                  Enable coding
                </button>
              ) : null}
              {isOwner && conversation.coding_enabled && !hasRepository ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                  onClick={() => {
                    setMenuOpen(false);
                    setAttachRepositoryOpen(true);
                  }}
                >
                  <Link2 className="h-3.5 w-3.5" />
                  Attach repository
                </button>
              ) : null}
              {isOwner && conversation.coding_enabled && hasRepository ? (
                <>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                    onClick={() => {
                      setMenuOpen(false);
                      setChangeRepositoryOpen(true);
                    }}
                  >
                    <Link2 className="h-3.5 w-3.5" />
                    Change repository
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                    disabled={detachRepositoryMutation.isPending}
                    onClick={() => detachRepositoryMutation.mutate()}
                  >
                    <Unlink className="h-3.5 w-3.5" />
                    Detach repository
                  </button>
                </>
              ) : null}
              {isOwner && conversation.coding_enabled ? (
                <button
                  type="button"
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-[var(--color-accent)]"
                  onClick={() => {
                    setMenuOpen(false);
                    setDisableCodingOpen(true);
                  }}
                >
                  <Code2 className="h-3.5 w-3.5" />
                  Disable coding
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px] text-[var(--color-muted-foreground)]">
        {conversation.coding_enabled ? (
          <>
            <span className="font-medium text-[var(--color-foreground)]">Coding workspace</span>
            <span aria-hidden="true">•</span>
            {hasRepository ? (
              <>
                <span>Repository:</span>
                <Link
                  to={`/repositories/${conversation.repository!.id}`}
                  className="truncate font-medium text-[var(--color-foreground)] hover:underline"
                >
                  {conversation.repository!.name}
                </Link>
                {defaultRepositoryBranch ? (
                  <>
                    <span aria-hidden="true">•</span>
                    <span>Branch {defaultRepositoryBranch.name}</span>
                  </>
                ) : null}
                {branchMemory ? (
                  <>
                    <span aria-hidden="true">•</span>
                    <MetaBadge>{formatSyncStatus(branchMemory.sync_status)}</MetaBadge>
                    <span aria-hidden="true">•</span>
                    <span>Memory v{branchMemory.memory_version}</span>
                  </>
                ) : (
                  <>
                    <span aria-hidden="true">•</span>
                    <MetaBadge>Not Synced</MetaBadge>
                  </>
                )}
              </>
            ) : (
              <>
                <span>Repository: None</span>
                <span aria-hidden="true">•</span>
                <span>Status: Local workspace</span>
              </>
            )}
            <span aria-hidden="true">•</span>
          </>
        ) : null}
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

      {isOwner ? (
        <>
          <EnableCodingDialog
            conversation={conversation}
            open={enableCodingOpen}
            onOpenChange={setEnableCodingOpen}
          />
          <AttachRepositoryDialog
            conversation={conversation}
            open={attachRepositoryOpen}
            onOpenChange={setAttachRepositoryOpen}
          />
          <AttachRepositoryDialog
            conversation={conversation}
            open={changeRepositoryOpen}
            onOpenChange={setChangeRepositoryOpen}
            title="Change repository"
            description="Attach a different repository to this coding workspace."
            confirmLabel="Change repository"
          />
          <DisableCodingDialog
            conversation={conversation}
            open={disableCodingOpen}
            onOpenChange={setDisableCodingOpen}
          />
        </>
      ) : null}
    </div>
  );
}
