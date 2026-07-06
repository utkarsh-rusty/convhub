import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { conversationApi, projectApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Skeleton } from "@/components/ui/skeleton";

export function HomePage() {
  const { activeWorkspaceId, workspaces, isLoading: workspacesLoading } = useWorkspace();

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

  if (workspacesLoading || projectsLoading || conversationsLoading) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }

  if (!workspaces.length) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-muted-foreground)]">
        Create a workspace to get started.
      </div>
    );
  }

  if (conversations[0]) {
    return <Navigate to={`/c/${conversations[0].id}`} replace />;
  }

  if (projects[0]) {
    return <Navigate to={`/projects/${projects[0].id}`} replace />;
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-muted-foreground)]">
      Create your first project from the sidebar.
    </div>
  );
}
