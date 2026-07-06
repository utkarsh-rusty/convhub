import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { RotateCcw, X } from "lucide-react";

import { conversationApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { RestoreContextDialog } from "@/components/conversation/restore-context-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface CommitDetailDrawerProps {
  commitHash: string | null;
  open: boolean;
  onClose: () => void;
}

export function CommitDetailDrawer({ commitHash, open, onClose }: CommitDetailDrawerProps) {
  const [restoreOpen, setRestoreOpen] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["commit", commitHash],
    queryFn: () => conversationApi.getCommit(commitHash!),
    enabled: Boolean(open && commitHash),
  });

  const { data: sourceConversation } = useQuery({
    queryKey: ["conversation", data?.conversation_id],
    queryFn: () => conversationApi.get(data!.conversation_id),
    enabled: Boolean(data?.conversation_id),
  });

  return (
    <div
      className={cn(
        "fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-[var(--color-border)] bg-[var(--color-card)] shadow-xl transition-transform duration-200 ease-out",
        open ? "translate-x-0" : "translate-x-full",
      )}
      aria-hidden={!open}
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
        <h2 className="text-sm font-semibold">Commit details</h2>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {!open ? null : isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : isError || !data ? (
          <p className="text-sm text-[var(--color-muted-foreground)]">Unable to load commit.</p>
        ) : (
          <div className="space-y-4 text-sm">
            <div>
              <p className="font-mono text-xs text-[var(--color-muted-foreground)]">
                {data.commit_hash}
              </p>
              <h3 className="mt-1 text-base font-semibold">{data.title}</h3>
              {data.description ? (
                <p className="mt-2 text-[var(--color-muted-foreground)]">{data.description}</p>
              ) : null}
            </div>

            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-xs">
              <dt className="text-[var(--color-muted-foreground)]">Author</dt>
              <dd>{data.created_by_name}</dd>
              <dt className="text-[var(--color-muted-foreground)]">Timestamp</dt>
              <dd>{formatTimestamp(data.created_at)}</dd>
              <dt className="text-[var(--color-muted-foreground)]">Branch</dt>
              <dd>
                <Link
                  to={`/c/${data.conversation_id}`}
                  className="text-[var(--color-foreground)] underline-offset-2 hover:underline"
                >
                  {data.conversation_title}
                </Link>
              </dd>
              <dt className="text-[var(--color-muted-foreground)]">Provider / model</dt>
              <dd>
                {data.range_metadata.providers.join(", ") || "None"}
                {data.range_metadata.models.length
                  ? ` · ${data.range_metadata.models.join(", ")}`
                  : ""}
              </dd>
              <dt className="text-[var(--color-muted-foreground)]">Execution</dt>
              <dd>{data.range_metadata.execution_types.join(", ") || "None"}</dd>
              <dt className="text-[var(--color-muted-foreground)]">Credits</dt>
              <dd>{data.range_metadata.credits_used}</dd>
              <dt className="text-[var(--color-muted-foreground)]">Borrowed</dt>
              <dd>
                {data.range_metadata.borrowed_requests > 0
                  ? `Yes (${data.range_metadata.borrowed_requests})`
                  : "No"}
                {data.range_metadata.borrowed_from.length
                  ? ` · ${data.range_metadata.borrowed_from.join(", ")}`
                  : ""}
              </dd>
              {data.parent_commit_hash ? (
                <>
                  <dt className="text-[var(--color-muted-foreground)]">Parent</dt>
                  <dd className="font-mono">{data.parent_commit_hash}</dd>
                </>
              ) : null}
            </dl>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-muted)]/20 px-3 py-3">
              <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
                Messages introduced
              </p>
              <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">
                Latest message in this commit:
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm">{data.message.content}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button asChild variant="outline" size="sm" className="h-7 text-xs">
                  <Link
                    to={`/c/${data.conversation_id}?message=${data.latest_message_id}&commit=${data.commit_hash}`}
                  >
                    Open in conversation
                  </Link>
                </Button>
                {data.context_package_id ? (
                  <>
                    <Button asChild variant="outline" size="sm" className="h-7 text-xs">
                      <Link to={`/context-packages/${data.context_package_id}`}>
                        View Context Package
                      </Link>
                    </Button>
                    <Button
                      type="button"
                      variant="default"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setRestoreOpen(true)}
                    >
                      <RotateCcw className="mr-1 h-3 w-3" />
                      Restore Context
                    </Button>
                  </>
                ) : null}
              </div>
            </div>
          </div>
        )}
      </div>

      {data?.context_package_id ? (
        <RestoreContextDialog
          packageId={data.context_package_id}
          defaultName={`Restored: ${data.title}`}
          defaultProjectId={sourceConversation?.project_id}
          open={restoreOpen}
          onOpenChange={setRestoreOpen}
        />
      ) : null}
    </div>
  );
}
