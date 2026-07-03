import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-5">
      <p className="text-xs uppercase tracking-wide text-[var(--color-muted-foreground)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export function ConversationStatsPage() {
  const { conversationId } = useParams();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversation-stats", conversationId],
    queryFn: () => conversationApi.getStats(conversationId!),
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
          <h1 className="text-xl font-semibold">Branch Statistics</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Read-only activity summary for this conversation.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-24 w-full" />
          ))}
        </div>
      ) : isError || !data ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">Unable to load statistics.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Messages" value={data.message_count} />
            <StatCard label="Participants" value={data.participants} />
            <StatCard label="Providers" value={data.providers_used.length || "None"} />
            <StatCard label="Credits Used" value={data.credits_used} />
            <StatCard label="Borrowed Requests" value={data.borrowed_requests} />
            <StatCard label="Assistant Messages" value={data.assistant_messages} />
          </div>
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4 text-sm text-[var(--color-muted-foreground)]">
            <p>User messages: {data.user_messages}</p>
            <p className="mt-1">
              Providers used: {data.providers_used.length ? data.providers_used.join(", ") : "None"}
            </p>
            <p className="mt-1">Latest activity: {formatTimestamp(data.latest_activity)}</p>
          </div>
        </div>
      )}
    </div>
  );
}
