import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Skeleton } from "@/components/ui/skeleton";

export function HomePage() {
  const { activeWorkspaceId, workspaces, isLoading: workspacesLoading } = useWorkspace();

  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ["conversations", activeWorkspaceId],
    queryFn: conversationApi.list,
    enabled: Boolean(activeWorkspaceId),
  });

  if (workspacesLoading || isLoading) {
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

  return (
    <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-[var(--color-muted-foreground)]">
      Create your first conversation from the sidebar.
    </div>
  );
}
