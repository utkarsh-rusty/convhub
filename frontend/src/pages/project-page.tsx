import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FolderKanban, GitBranch, MessageSquare, Package, RotateCcw } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { projectApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useWorkspace } from "@/context/workspace-context";
import { CreateConversationDialog } from "@/components/conversation/create-conversation-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function ProjectPage() {
  const { projectId } = useParams();
  const { activeWorkspaceId } = useWorkspace();
  const [createOpen, setCreateOpen] = useState(false);

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ["projects", activeWorkspaceId, projectId],
    queryFn: () => projectApi.get(projectId!),
    enabled: Boolean(activeWorkspaceId && projectId),
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

  if (isError || !project) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Project not found.
      </div>
    );
  }

  const accent = project.color || "#64748b";

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div className="border-b border-[var(--color-border)] px-6 py-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-white"
              style={{ backgroundColor: accent }}
            >
              <FolderKanban className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
                {project.is_default ? (
                  <span className="rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
                    Default
                  </span>
                ) : null}
              </div>
              <p className="mt-1 max-w-2xl text-sm text-[var(--color-muted-foreground)]">
                {project.description || "No description yet."}
              </p>
              <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">
                Last activity{" "}
                {project.last_activity_at
                  ? formatTimestamp(project.last_activity_at)
                  : "—"}
              </p>
            </div>
          </div>
          <Button type="button" onClick={() => setCreateOpen(true)}>
            New conversation
          </Button>
        </div>
      </div>

      <div className="space-y-8 px-6 py-6">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={MessageSquare}
            label="Conversations"
            value={project.conversation_count}
          />
          <StatCard icon={GitBranch} label="Branches" value={project.branch_count} />
          <StatCard label="Commits" value={project.commit_count} />
          <StatCard
            icon={Package}
            label="Context Packages"
            value={project.context_package_count}
          />
        </div>

        <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
          <div>
            <h2 className="mb-3 text-sm font-medium">Recent conversations</h2>
            {project.recent_conversations.length === 0 ? (
              <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
                No conversations in this project yet.
              </p>
            ) : (
              <div className="divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
                {project.recent_conversations.map((conversation) => (
                  <Link
                    key={conversation.id}
                    to={`/c/${conversation.id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[var(--color-accent)]"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate text-sm font-medium">{conversation.title}</p>
                        {conversation.is_restored ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-sky-500/10 px-1.5 py-0.5 text-[10px] font-medium text-sky-700 dark:text-sky-300">
                            <RotateCcw className="h-2.5 w-2.5" />
                            Restored
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-0.5 text-xs text-[var(--color-muted-foreground)]">
                        {conversation.commit_count} commits ·{" "}
                        {formatTimestamp(conversation.last_activity_at)}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div>
            <h2 className="mb-3 text-sm font-medium">Workspace members</h2>
            <div className="divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
              {project.members.map((member) => (
                <div key={member.user_id} className="px-4 py-3">
                  <p className="text-sm font-medium">{member.name}</p>
                  <p className="text-xs text-[var(--color-muted-foreground)]">{member.email}</p>
                  <p className="mt-0.5 text-[10px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                    {member.role}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>

      <CreateConversationDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        defaultProjectId={project.id}
      />
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon?: typeof MessageSquare;
}) {
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4">
      <div className="flex items-center gap-2 text-[var(--color-muted-foreground)]">
        {Icon ? <Icon className="h-4 w-4" /> : null}
        <p className="text-sm">{label}</p>
      </div>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
