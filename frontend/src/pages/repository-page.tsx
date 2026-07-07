import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2, GitBranch, Link as LinkIcon, Plus } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";

import {
  conversationApi,
  repositoryApi,
  repositoryBranchApi,
  showApiError,
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
import type { BranchMemorySummary, RepositoryBranchResponse } from "@/types/api";

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

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["repository-branches", activeWorkspaceId] });
    void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
  };

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
}: {
  branch: RepositoryBranchResponse;
  memory?: BranchMemorySummary | null;
  onRename: () => void;
  onArchive: () => void;
  onRestore: () => void;
  onExport: () => void;
}) {
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
        <MemoryField label="Memory version" value={String(memory?.memory_version ?? 1)} />
      </div>
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
