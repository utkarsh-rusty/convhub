import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function ConversationTimelinePage() {
  const { conversationId } = useParams();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["conversation-timeline", conversationId],
    queryFn: () => conversationApi.getTimeline(conversationId!),
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
          <h1 className="text-xl font-semibold">Timeline</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Chronological history derived from existing conversation metadata.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : isError || !data ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">Unable to load timeline.</p>
      ) : (
        <ol className="relative space-y-4 border-l border-[var(--color-border)] pl-6">
          {data.events.map((event, index) => (
            <li key={`${event.event_type}-${event.occurred_at}-${index}`} className="relative">
              <span className="absolute -left-[1.9rem] top-1.5 h-3 w-3 rounded-full border border-[var(--color-border)] bg-[var(--color-primary)]" />
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium">{event.event_type}</p>
                  <span className="text-xs text-[var(--color-muted-foreground)]">
                    {formatTimestamp(event.occurred_at)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">{event.summary}</p>
                {event.actor_name ? (
                  <p className="mt-1 text-xs text-[var(--color-muted-foreground)]">
                    Actor: {event.actor_name}
                  </p>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
