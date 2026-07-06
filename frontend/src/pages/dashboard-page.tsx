import { useQuery } from "@tanstack/react-query";
import { FolderKanban } from "lucide-react";
import { Link } from "react-router-dom";

import { conversationApi, projectApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useWorkspace } from "@/context/workspace-context";
import { useSocket } from "@/context/socket-context";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardPage() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const { status } = useSocket();

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ["projects", activeWorkspaceId],
    queryFn: () => projectApi.list(),
    enabled: Boolean(activeWorkspaceId),
  });

  const { data: conversations = [], isLoading: conversationsLoading } = useQuery({
    queryKey: ["conversations", activeWorkspaceId],
    queryFn: conversationApi.list,
    enabled: Boolean(activeWorkspaceId),
  });

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to view the dashboard.
      </div>
    );
  }

  const isLoading = projectsLoading || conversationsLoading;
  const recentConversations = [...conversations]
    .sort(
      (a, b) =>
        new Date(b.last_activity_at).getTime() - new Date(a.last_activity_at).getTime(),
    )
    .slice(0, 8);
  const projectNameById = new Map(projects.map((project) => [project.id, project.name]));

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-[var(--color-border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Workspace Dashboard</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          {activeWorkspace?.name ?? "Workspace"} · Projects and recent conversations · Live{" "}
          {status}
        </p>
      </div>

      <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <>
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-medium">Projects</h3>
                <span className="text-xs text-[var(--color-muted-foreground)]">
                  {projects.length} total
                </span>
              </div>
              {projects.length === 0 ? (
                <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
                  No projects yet.
                </p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {projects.map((project) => (
                    <Link
                      key={project.id}
                      to={`/projects/${project.id}`}
                      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4 transition-colors hover:bg-[var(--color-accent)]"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white"
                          style={{ backgroundColor: project.color || "#64748b" }}
                        >
                          <FolderKanban className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium">{project.name}</p>
                          <p className="mt-0.5 line-clamp-2 text-xs text-[var(--color-muted-foreground)]">
                            {project.description || "No description"}
                          </p>
                          <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">
                            {project.conversation_count} conversations ·{" "}
                            {project.commit_count} commits
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h3 className="mb-3 text-sm font-medium">Recent conversations</h3>
              {recentConversations.length === 0 ? (
                <p className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-sm text-[var(--color-muted-foreground)]">
                  No conversations yet.
                </p>
              ) : (
                <div className="divide-y divide-[var(--color-border)] rounded-lg border border-[var(--color-border)]">
                  {recentConversations.map((conversation) => (
                    <Link
                      key={conversation.id}
                      to={`/c/${conversation.id}`}
                      className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-[var(--color-accent)]"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{conversation.title}</p>
                        <p className="mt-0.5 text-xs text-[var(--color-muted-foreground)]">
                          {projectNameById.get(conversation.project_id) ?? "Project"} ·{" "}
                          {formatTimestamp(conversation.last_activity_at)}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
