import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function ConversationHistoryPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const { data: commits = [], isLoading, isError } = useQuery({
    queryKey: ["conversation-commits", conversationId],
    queryFn: () => conversationApi.listCommits(conversationId!),
    enabled: Boolean(conversationId),
  });

  if (!conversationId) {
    return null;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col px-6 py-6">
      <div className="mb-6 flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to={`/c/${conversationId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div>
          <h1 className="text-xl font-semibold">Conversation History</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Manual commits for this conversation.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : isError ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">Unable to load commits.</p>
      ) : commits.length === 0 ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">
          No commits yet. Create one from the conversation header.
        </p>
      ) : (
        <ol className="relative space-y-0 border-l border-[var(--color-border)] pl-6">
          {commits.map((commit, index) => (
            <li key={commit.commit_hash} className="relative pb-6">
              <span className="absolute -left-[1.9rem] top-1.5 h-3 w-3 rounded-full border border-[var(--color-border)] bg-[var(--color-primary)]" />
              <button
                type="button"
                className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3 text-left hover:bg-[var(--color-accent)]"
                onClick={() =>
                  navigate(`/c/${conversationId}?message=${commit.latest_message_id}&commit=${commit.commit_hash}`)
                }
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold">○ {commit.commit_hash}</span>
                  <span className="text-sm font-medium">{commit.title}</span>
                </div>
                <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">
                  {commit.created_by_name} · {formatTimestamp(commit.created_at)}
                </p>
                {commit.description ? (
                  <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                    {commit.description}
                  </p>
                ) : null}
              </button>
              {index < commits.length - 1 ? (
                <div className="ml-1 mt-2 text-[var(--color-muted-foreground)]">│</div>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
