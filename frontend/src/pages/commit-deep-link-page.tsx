import { useQuery } from "@tanstack/react-query";
import { Navigate, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

export function CommitDeepLinkPage() {
  const { commitHash } = useParams();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["commit", commitHash],
    queryFn: () => conversationApi.getCommit(commitHash!),
    enabled: Boolean(commitHash),
  });

  if (!commitHash) {
    return <Navigate to="/app" replace />;
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-4 px-6 py-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full max-w-xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Commit not found in this workspace.
      </div>
    );
  }

  return (
    <Navigate
      to={`/c/${data.conversation_id}?message=${data.latest_message_id}&commit=${data.commit_hash}`}
      replace
    />
  );
}
