import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2, GitBranch, Link as LinkIcon } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, repositoryApi, showApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

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

export function RepositoryPage() {
  const { repositoryId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const { data: repository, isLoading, isError } = useQuery({
    queryKey: ["repositories", activeWorkspaceId, repositoryId],
    queryFn: () => repositoryApi.get(repositoryId!),
    enabled: Boolean(activeWorkspaceId && repositoryId),
  });

  const createLinkedConversation = useMutation({
    mutationFn: async () => {
      if (!repository) {
        throw new Error("Repository not loaded");
      }
      const conversation = await conversationApi.create({ project_id: repository.project_id });
      return conversationApi.enableCoding(conversation.id, {
        existing_repository_id: repository.id,
      });
    },
    onSuccess: (conversation) => {
      toast.success("Coding conversation created");
      void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      navigate(`/c/${conversation.id}`);
    },
    onError: (error) => showApiError(error, "Unable to create coding conversation"),
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
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <InfoCard label="Default branch" value={repository.default_branch} />
          <InfoCard label="Connected conversations" value={String(repository.conversation_count)} />
          <InfoCard label="Latest commit" value="Not Available Yet" muted />
          <InfoCard label="Sync status" value="Not Synced" muted />
        </div>

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
    </div>
  );
}

function InfoCard({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
        {label}
      </p>
      <p
        className={
          muted
            ? "mt-1 text-sm text-[var(--color-muted-foreground)]"
            : "mt-1 text-lg font-semibold"
        }
      >
        {value}
      </p>
    </div>
  );
}
