import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2, GitBranch, History, Link as LinkIcon, Plus, RefreshCw, Upload } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import {
  conversationApi,
  repositoryApi,
  repositoryBranchApi,
  showApiError,
  syncApi,
} from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  BranchMemorySummary,
  BranchSyncRecordSummary,
  RepositoryBranchResponse,
  WorkspaceSessionResponse,
} from "@/types/api";

function providerLabel(provider: string) {
  switch (provider) {
    case "github":
      return "GitHub";
    case "gitlab":
      return "GitLab";
    case "bitbucket":
      return "Bitbucket";
    default:
      return "Other";
  }
}

function syncStateLabel(state: string) {
  switch (state) {
    case "synced":
      return "Synced";
    case "ahead":
      return "Ahead";
    case "behind":
      return "Behind";
    case "conflict":
      return "Conflict";
    case "detached":
      return "Detached";
    default:
      return state;
  }
}

function syncStatusLabel(status: string) {
  switch (status) {
    case "not_synced":
      return "Not Synced";
    case "ready":
      return "Ready";
    case "outdated":
      return "Outdated";
    case "in_progress":
      return "In Progress";
    case "conflict":
      return "Conflict";
    default:
      return status;
  }
}

function sessionStatusLabel(status: string) {
  switch (status) {
    case "active":
      return "Active";
    case "idle":
      return "Idle";
    case "disconnected":
      return "Disconnected";
    case "closed":
      return "Closed";
    default:
      return status;
  }
}

function syncTypeLabel(syncType: string) {
  switch (syncType) {
    case "local_commit":
      return "Local Commit";
    case "restore":
      return "Restore";
    case "attach_repository":
      return "Attach Repository";
    case "detach_repository":
      return "Detach Repository";
    case "plugin_push":
      return "Plugin Push";
    case "plugin_pull":
      return "Plugin Pull";
    case "manual_update":
      return "Manual Update";
    default:
      return syncType;
  }
}

export function RepositoryPage() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [createBranchOpen, setCreateBranchOpen] = useState(false);
  const [newBranchName, setNewBranchName] = useState("");
  const [renameBranch, setRenameBranch] = useState<RepositoryBranchResponse | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const { data: repository, isLoading, isError } = useQuery({
    queryKey: ["repositories", activeWorkspaceId, repositoryId],
    queryFn: () => repositoryApi.get(repositoryId!),
    enabled: Boolean(activeWorkspaceId && repositoryId),
  });

  const { data: branches = [], isLoading: branchesLoading } = useQuery({
    queryKey: ["repository-branches", activeWorkspaceId, repositoryId],
    queryFn: () => repositoryApi.listBranches(repositoryId!, true),
    enabled: Boolean(activeWorkspaceId && repositoryId),
  });

  const { data: workspaceSessions = [], isLoading: sessionsLoading } = useQuery({
    queryKey: ["workspace-sessions", activeWorkspaceId, repositoryId],
    queryFn: () => repositoryApi.listWorkspaceSessions(repositoryId!),
    enabled: Boolean(activeWorkspaceId && repositoryId),
  });

  const { data: protocolStatus } = useQuery({
    queryKey: ["workspace-client-status", activeWorkspaceId, repositoryId],
    queryFn: () => repositoryApi.getWorkspaceClientStatus(repositoryId!),
    enabled: Boolean(activeWorkspaceId && repositoryId),
  });

  const defaultBranch = branches.find((branch) => branch.is_default) ?? branches[0] ?? null;

  const { data: syncStatus, isLoading: syncLoading } = useQuery({
    queryKey: ["sync-status", activeWorkspaceId, defaultBranch?.id],
    queryFn: () => syncApi.getStatus(defaultBranch!.id),
    enabled: Boolean(activeWorkspaceId && defaultBranch?.id),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["repository-branches", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["sync-status", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["workspace-sessions", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["workspace-client-status", activeWorkspaceId] });
  };

  const pushSyncMutation = useMutation({
    mutationFn: () => syncApi.push(defaultBranch!.id),
    onSuccess: () => {
      toast.success("Sync push registered");
      invalidate();
    },
    onError: (error) => showApiError(error, "Unable to register sync push"),
  });

  const pullSyncMutation = useMutation({
    mutationFn: () => syncApi.pull(defaultBranch!.id),
    onSuccess: () => {
      toast.success("Sync pull metadata loaded");
      invalidate();
    },
    onError: (error) => showApiError(error, "Unable to load sync pull metadata"),
  });

  const createLinkedConversation = useMutation({
    mutationFn: async () => {
      if (!repository) {
        throw new Error("Repository not loaded");
      }
      const conversation = await conversationApi.create({ project_id: repository.project_id });
      await conversationApi.enableCoding(conversation.id);
      return conversationApi.attachRepository(conversation.id, { repository_id: repository.id });
    },
    onSuccess: (conversation) => {
      toast.success("Coding conversation created");
      invalidate();
      navigate(`/c/${conversation.id}`);
    },
    onError: (error) => showApiError(error, "Unable to create coding conversation"),
  });

  const createBranchMutation = useMutation({
    mutationFn: () => repositoryApi.createBranch(repositoryId!, { name: newBranchName.trim() }),
    onSuccess: () => {
      toast.success("Repository branch created");
      setCreateBranchOpen(false);
      setNewBranchName("");
      invalidate();
    },
    onError: (error) => showApiError(error, "Unable to create repository branch"),
  });

  const renameBranchMutation = useMutation({
    mutationFn: () => repositoryBranchApi.rename(renameBranch!.id, { name: renameValue.trim() }),
    onSuccess: () => {
      toast.success("Repository branch renamed");
      setRenameBranch(null);
      invalidate();
    },
    onError: (error) => showApiError(error, "Unable to rename repository branch"),
  });

  const archiveBranchMutation = useMutation({
    mutationFn: (branchId: string) => repositoryBranchApi.archive(branchId),
    onSuccess: () => {
      toast.success("Repository branch archived");
      invalidate();
    },
    onError: (error) => showApiError(error, "Unable to archive repository branch"),
  });

  const restoreBranchMutation = useMutation({
    mutationFn: (branchId: string) => repositoryBranchApi.restore(branchId),
    onSuccess: () => {
      toast.success("Repository branch restored");
      invalidate();
    },
    onError: (error) => showApiError(error, "Unable to restore repository branch"),
  });

  const exportMemoryMutation = useMutation({
    mutationFn: (branchId: string) => repositoryBranchApi.exportMemory(branchId),
    onSuccess: (payload) => {
      const blob = new Blob([JSON.stringify(payload.content, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = payload.filename;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Branch memory exported");
    },
    onError: (error) => showApiError(error, "Unable to export branch memory"),
  });

  const exportHistoryMutation = useMutation({
    mutationFn: (branchId: string) => repositoryBranchApi.exportHistory(branchId),
    onSuccess: (payload) => {
      const blob = new Blob([JSON.stringify(payload.content, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = payload.filename;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Branch history exported");
    },
    onError: (error) => showApiError(error, "Unable to export branch history"),
  });

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isError || !repository) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Repository not found.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="border-b border-[var(--color-border)] px-6 py-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-white">
              <Code2 className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight">{repository.name}</h1>
                <span className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
                  {providerLabel(repository.provider)}
                </span>
              </div>
              <p className="mt-1 font-mono text-sm text-[var(--color-muted-foreground)]">
                {repository.owner}/{repository.repository_name}
              </p>
              <a
                href={repository.remote_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs text-[var(--color-muted-foreground)] hover:text-[var(--color-foreground)]"
              >
                <LinkIcon className="h-3 w-3" />
                {repository.remote_url}
              </a>
            </div>
          </div>
          <Button
            type="button"
            disabled={createLinkedConversation.isPending}
            onClick={() => createLinkedConversation.mutate()}
          >
            {createLinkedConversation.isPending ? "Creating..." : "New coding conversation"}
          </Button>
        </div>
      </div>

      <div className="space-y-8 px-6 py-6">
        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">Sync</h2>
            {defaultBranch ? (
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={pushSyncMutation.isPending || !defaultBranch}
                  onClick={() => pushSyncMutation.mutate()}
                >
                  <Upload className="mr-1.5 h-3.5 w-3.5" />
                  {pushSyncMutation.isPending ? "Pushing..." : "Push"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={pullSyncMutation.isPending || !defaultBranch}
                  onClick={() => pullSyncMutation.mutate()}
                >
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                  {pullSyncMutation.isPending ? "Pulling..." : "Pull"}
                </Button>
              </div>
            ) : null}
          </div>

          {!defaultBranch ? (
            <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
              Create a repository branch to view synchronization status.
            </p>
          ) : syncLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <div className="rounded-lg border border-[var(--color-border)] p-4">
              <div className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
                <MemoryField
                  label="Sync state"
                  value={syncStateLabel(syncStatus?.sync_state ?? "detached")}
                />
                <MemoryField
                  label="Branch version"
                  value={syncStatus?.sync_version != null ? String(syncStatus.sync_version) : "—"}
                />
                <MemoryField
                  label="Last sync"
                  value={
                    syncStatus?.last_synchronized_at
                      ? formatTimestamp(syncStatus.last_synchronized_at)
                      : "—"
                  }
                />
                <MemoryField
                  label="Latest commit"
                  value={
                    syncStatus?.latest_commit
                      ? `#${syncStatus.latest_commit.commit_hash}`
                      : "Not Available Yet"
                  }
                />
                <MemoryField
                  label="Latest context package"
                  value={
                    syncStatus?.latest_context_package
                      ? `v${syncStatus.latest_context_package.version}`
                      : "Not Available Yet"
                  }
                />
                <MemoryField
                  label="Repository branch"
                  value={syncStatus?.repository_branch.name ?? defaultBranch.name}
                />
              </div>
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium">Plugin Protocol</h2>
          <div className="rounded-lg border border-[var(--color-border)] p-4">
            <div className="grid gap-3 text-xs sm:grid-cols-3">
              <MemoryField
                label="Plugin Protocol Ready"
                value={protocolStatus?.plugin_protocol_ready ? "Ready" : "—"}
              />
              <MemoryField
                label="Connected Sessions"
                value={
                  protocolStatus?.connected_sessions != null
                    ? String(protocolStatus.connected_sessions)
                    : String(workspaceSessions.length)
                }
              />
              <MemoryField
                label="Current Sync Version"
                value={
                  protocolStatus?.current_sync_version != null
                    ? String(protocolStatus.current_sync_version)
                    : syncStatus?.sync_version != null
                      ? String(syncStatus.sync_version)
                      : "—"
                }
              />
            </div>
          </div>
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium">Active Developers</h2>
          {sessionsLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : workspaceSessions.length === 0 ? (
            <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
              No active workspace sessions.
            </p>
          ) : (
            <div className="divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
              {workspaceSessions.map((session) => (
                <ActiveDeveloperRow key={session.id} session={session} />
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">Branches</h2>
            <Button type="button" size="sm" variant="outline" onClick={() => setCreateBranchOpen(true)}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Create branch
            </Button>
          </div>

          {branchesLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : branches.length === 0 ? (
            <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
              No repository branches yet.
            </p>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {branches.map((branch) => (
                <BranchMemoryCard
                  key={branch.id}
                  branch={branch}
                  memory={branch.memory}
                  onRename={() => {
                    setRenameBranch(branch);
                    setRenameValue(branch.name);
                  }}
                  onArchive={() => archiveBranchMutation.mutate(branch.id)}
                  onRestore={() => restoreBranchMutation.mutate(branch.id)}
                  onExport={() => exportMemoryMutation.mutate(branch.id)}
                  onExportHistory={() => exportHistoryMutation.mutate(branch.id)}
                />
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium">Connected conversations</h2>
          {repository.connected_conversations.length === 0 ? (
            <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
              No conversations are linked to this repository yet.
            </p>
          ) : (
            <div className="divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
              {repository.connected_conversations.map((conversation) => (
                <Link
                  key={conversation.id}
                  to={`/c/${conversation.id}`}
                  className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[var(--color-accent)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {conversation.branch_name || conversation.title}
                    </p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">
                      {conversation.message_count} messages · {conversation.commit_count} commits
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[var(--color-muted-foreground)]">
                    {conversation.branch_name ? <GitBranch className="h-3.5 w-3.5" /> : null}
                    <span>{formatTimestamp(conversation.last_activity_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      <Dialog open={createBranchOpen} onOpenChange={setCreateBranchOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create repository branch</DialogTitle>
            <DialogDescription>
              Register a Git branch for this repository. Branch Memory will be created automatically.
            </DialogDescription>
          </DialogHeader>
          <Input
            value={newBranchName}
            onChange={(event) => setNewBranchName(event.target.value)}
            placeholder="feature/login"
          />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setCreateBranchOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!newBranchName.trim() || createBranchMutation.isPending}
              onClick={() => createBranchMutation.mutate()}
            >
              {createBranchMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={renameBranch !== null} onOpenChange={(open) => !open && setRenameBranch(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename repository branch</DialogTitle>
          </DialogHeader>
          <Input value={renameValue} onChange={(event) => setRenameValue(event.target.value)} />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setRenameBranch(null)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!renameValue.trim() || renameBranchMutation.isPending}
              onClick={() => renameBranchMutation.mutate()}
            >
              {renameBranchMutation.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function BranchMemoryCard({
  branch,
  memory,
  onRename,
  onArchive,
  onRestore,
  onExport,
  onExportHistory,
}: {
  branch: RepositoryBranchResponse;
  memory?: BranchMemorySummary | null;
  onRename: () => void;
  onArchive: () => void;
  onRestore: () => void;
  onExport: () => void;
  onExportHistory: () => void;
}) {
  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ["repository-branch-history", branch.id],
    queryFn: () => repositoryBranchApi.listHistory(branch.id),
  });

  const latestRecord = memory?.latest_sync_record ?? history[0] ?? null;

  return (
    <div className="rounded-lg border border-[var(--color-border)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-[var(--color-muted-foreground)]" />
            <h3 className="text-sm font-semibold">{branch.name}</h3>
            {branch.is_default ? (
              <span className="rounded-full border border-[var(--color-border)] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                Default
              </span>
            ) : null}
            {!branch.is_active ? (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-700 dark:text-amber-300">
                Archived
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">
            Sync status: {syncStatusLabel(memory?.sync_status ?? "not_synced")}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Button type="button" size="sm" variant="ghost" onClick={onExportHistory}>
            History
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onExport}>
            Export
          </Button>
          <Button type="button" size="sm" variant="ghost" onClick={onRename}>
            Rename
          </Button>
          {branch.is_active ? (
            <Button type="button" size="sm" variant="ghost" onClick={onArchive} disabled={branch.is_default}>
              Archive
            </Button>
          ) : (
            <Button type="button" size="sm" variant="ghost" onClick={onRestore}>
              Restore
            </Button>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-2 text-xs sm:grid-cols-2">
        <MemoryField
          label="Active conversation"
          value={
            memory?.current_conversation_id ? (
              <Link to={`/c/${memory.current_conversation_id}`} className="hover:underline">
                {memory.current_conversation_title ?? "Open conversation"}
              </Link>
            ) : (
              "—"
            )
          }
        />
        <MemoryField
          label="Active ConvHub branch"
          value={
            memory?.current_convhub_branch_id ? (
              <Link to={`/c/${memory.current_convhub_branch_id}`} className="hover:underline">
                {memory.current_convhub_branch_name ?? "Open branch"}
              </Link>
            ) : (
              "—"
            )
          }
        />
        <MemoryField
          label="Latest commit"
          value={memory?.current_commit_hash ? `#${memory.current_commit_hash}` : "Not Available Yet"}
        />
        <MemoryField
          label="Latest context package"
          value={
            memory?.current_context_package_version != null
              ? `v${memory.current_context_package_version}`
              : "Not Available Yet"
          }
        />
        <MemoryField label="Working developer" value={memory?.working_user_name ?? "—"} />
        <MemoryField label="Memory version" value={String(memory?.memory_version ?? 0)} />
      </div>

      <div className="mt-4 border-t border-[var(--color-border)] pt-4">
        <div className="mb-3 flex items-center gap-2">
          <History className="h-3.5 w-3.5 text-[var(--color-muted-foreground)]" />
          <h4 className="text-xs font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
            Latest sync record
          </h4>
        </div>
        {latestRecord ? (
          <SyncRecordRow record={latestRecord} compact />
        ) : (
          <p className="text-xs text-[var(--color-muted-foreground)]">No sync records yet.</p>
        )}
      </div>

      <div className="mt-4 border-t border-[var(--color-border)] pt-4">
        <h4 className="mb-3 text-xs font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
          Timeline
        </h4>
        {historyLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : history.length === 0 ? (
          <p className="text-xs text-[var(--color-muted-foreground)]">No history yet.</p>
        ) : (
          <div className="space-y-2">
            {history.map((record) => (
              <SyncRecordRow key={record.id} record={record} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SyncRecordRow({
  record,
  compact = false,
}: {
  record: BranchSyncRecordSummary;
  compact?: boolean;
}) {
  return (
    <div
      className={
        compact
          ? "rounded-md bg-[var(--color-muted)]/20 px-3 py-2 text-xs"
          : "rounded-md border border-[var(--color-border)] px-3 py-2 text-xs"
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-[var(--color-foreground)]">
          {syncTypeLabel(record.sync_type)}
        </span>
        <span className="text-[var(--color-muted-foreground)]">
          {formatTimestamp(record.created_at)}
        </span>
      </div>
      <div className={`mt-2 grid gap-1 ${compact ? "sm:grid-cols-2" : "sm:grid-cols-2 lg:grid-cols-3"}`}>
        <span>
          User: <span className="text-[var(--color-foreground)]">{record.user_name ?? "—"}</span>
        </span>
        <span>
          Conversation:{" "}
          {record.conversation_id ? (
            <Link to={`/c/${record.conversation_id}`} className="text-[var(--color-foreground)] hover:underline">
              {record.conversation_title ?? "Open"}
            </Link>
          ) : (
            "—"
          )}
        </span>
        <span>
          Commit:{" "}
          <span className="text-[var(--color-foreground)]">
            {record.commit_hash ? `#${record.commit_hash}` : "—"}
          </span>
        </span>
        <span>
          Context package:{" "}
          <span className="text-[var(--color-foreground)]">
            {record.context_package_version != null ? `v${record.context_package_version}` : "—"}
          </span>
        </span>
      </div>
    </div>
  );
}

function ActiveDeveloperRow({ session }: { session: WorkspaceSessionResponse }) {
  const clientLabel = [session.client_name, session.client_version].filter(Boolean).join(" ") || "—";

  return (
    <div className="grid gap-3 px-4 py-3 text-xs sm:grid-cols-2 lg:grid-cols-3">
      <MemoryField label="Developer" value={session.user_name ?? "Unknown"} />
      <MemoryField label="Repository branch" value={session.repository_branch_name ?? "—"} />
      <MemoryField label="Started" value={formatTimestamp(session.started_at)} />
      <MemoryField label="Last heartbeat" value={formatTimestamp(session.last_heartbeat_at)} />
      <MemoryField label="Session status" value={sessionStatusLabel(session.status)} />
      <MemoryField
        label="Client"
        value={
          <span>
            {clientLabel}
            {session.platform ? (
              <span className="text-[var(--color-muted-foreground)]"> · {session.platform}</span>
            ) : null}
          </span>
        }
      />
    </div>
  );
}

function MemoryField({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-md bg-[var(--color-muted)]/20 px-3 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
        {label}
      </p>
      <div className="mt-1 text-sm text-[var(--color-foreground)]">{value}</div>
    </div>
  );
}
