import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ChevronRight, Download } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, showApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function CollapsibleCard({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)]">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((value) => !value)}
      >
        <h2 className="text-sm font-semibold">{title}</h2>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      <div className={cn("border-t border-[var(--color-border)] px-4 py-3", !open && "hidden")}>
        {children}
      </div>
    </section>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function ContextPackagePage() {
  const { packageId } = useParams();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["context-package", packageId],
    queryFn: () => conversationApi.getContextPackage(packageId!),
    enabled: Boolean(packageId),
  });

  const exportJson = async () => {
    if (!packageId) {
      return;
    }
    try {
      const exported = await conversationApi.exportContextPackage(packageId);
      const blob = new Blob([JSON.stringify(exported, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `context-package-${packageId}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Context package exported");
    } catch (error) {
      showApiError(error, "Unable to export context package");
    }
  };

  if (!packageId) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="space-y-3 px-6 py-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="px-6 py-6 text-sm text-[var(--color-muted-foreground)]">
        Context package not found.
      </div>
    );
  }

  const metadata = asRecord(data.metadata);
  const summary = asRecord(data.summary);
  const statistics = asRecord(data.statistics);
  const commit = asRecord(metadata.commit);
  const conversation = asRecord(metadata.conversation);
  const participants = asArray(metadata.participants);
  const providers = asArray(statistics.providers_used);
  const borrowRecords = asArray(metadata.borrow_records);
  const snapshot = asArray(summary.conversation_snapshot);
  const architectureNotes = asArray(summary.architecture_notes);
  const decisions = asArray(summary.decisions);
  const todos = asArray(summary.todos);

  return (
    <div className="flex min-h-0 flex-1 flex-col px-4 py-4 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to={`/c/${data.conversation_id}/history`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold">Context Package</h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Immutable project-memory artifact for commit{" "}
            <span className="font-mono">{String(commit.commit_hash ?? "")}</span>
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => void exportJson()}>
          <Download className="mr-2 h-4 w-4" />
          Export JSON
        </Button>
      </div>

      <div className="space-y-3 overflow-y-auto pb-8">
        <CollapsibleCard title="Metadata">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="text-[var(--color-muted-foreground)]">Package ID</dt>
            <dd className="font-mono text-xs">{data.id}</dd>
            <dt className="text-[var(--color-muted-foreground)]">Status</dt>
            <dd>{data.status}</dd>
            <dt className="text-[var(--color-muted-foreground)]">Version</dt>
            <dd>{data.version}</dd>
            <dt className="text-[var(--color-muted-foreground)]">Generated</dt>
            <dd>{formatTimestamp(data.generated_at)}</dd>
            <dt className="text-[var(--color-muted-foreground)]">Commit</dt>
            <dd>
              {String(commit.title ?? "")}{" "}
              <span className="font-mono text-xs">({String(commit.commit_hash ?? "")})</span>
            </dd>
            <dt className="text-[var(--color-muted-foreground)]">Branch</dt>
            <dd>
              {String(conversation.branch_name ?? conversation.title ?? "Main")}
            </dd>
          </dl>
        </CollapsibleCard>

        <CollapsibleCard title="Conversation Summary">
          <p className="text-sm font-medium">{String(summary.title ?? "")}</p>
          {summary.description ? (
            <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
              {String(summary.description)}
            </p>
          ) : (
            <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">No description.</p>
          )}
        </CollapsibleCard>

        <CollapsibleCard title="Statistics">
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            {Object.entries(statistics).map(([key, value]) => (
              <div key={key} className="rounded-lg border border-[var(--color-border)] px-3 py-2">
                <p className="text-[11px] uppercase tracking-wide text-[var(--color-muted-foreground)]">
                  {key.replaceAll("_", " ")}
                </p>
                <p className="mt-1 font-medium">
                  {Array.isArray(value) ? value.join(", ") || "None" : String(value)}
                </p>
              </div>
            ))}
          </dl>
        </CollapsibleCard>

        <CollapsibleCard title="Participants">
          <ul className="space-y-1 text-sm">
            {participants.map((item) => {
              const participant = asRecord(item);
              return (
                <li key={String(participant.user_id)}>
                  {String(participant.name)}{" "}
                  <span className="text-[var(--color-muted-foreground)]">
                    ({String(participant.role)})
                  </span>
                </li>
              );
            })}
          </ul>
        </CollapsibleCard>

        <CollapsibleCard title="Providers">
          <p className="text-sm">
            {providers.length ? providers.map(String).join(", ") : "None recorded in this range."}
          </p>
        </CollapsibleCard>

        <CollapsibleCard title="Credits">
          <p className="text-sm">
            Credits used:{" "}
            <span className="font-medium">{String(statistics.credits_used ?? "0")}</span>
          </p>
        </CollapsibleCard>

        <CollapsibleCard title="Borrow Information">
          {borrowRecords.length === 0 ? (
            <p className="text-sm text-[var(--color-muted-foreground)]">No borrow records.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {borrowRecords.map((item) => {
                const record = asRecord(item);
                return (
                  <li key={String(record.request_id)}>
                    Lender {String(record.lender_name)} · request{" "}
                    <span className="font-mono text-xs">{String(record.request_id)}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </CollapsibleCard>

        <CollapsibleCard title="Conversation Snapshot" defaultOpen={false}>
          <div className="space-y-2">
            {snapshot.map((item) => {
              const message = asRecord(item);
              return (
                <div
                  key={String(message.id)}
                  className="rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm"
                >
                  <p className="text-[11px] uppercase text-[var(--color-muted-foreground)]">
                    {String(message.role)}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap">{String(message.content)}</p>
                </div>
              );
            })}
          </div>
        </CollapsibleCard>

        <CollapsibleCard title="Architecture Notes">
          <p className="text-sm text-[var(--color-muted-foreground)]">
            {architectureNotes.length === 0 ? "Empty — reserved for future decision capture." : null}
          </p>
        </CollapsibleCard>

        <CollapsibleCard title="Decisions">
          <p className="text-sm text-[var(--color-muted-foreground)]">
            {decisions.length === 0 ? "Empty — reserved for future decision tracking." : null}
          </p>
        </CollapsibleCard>

        <CollapsibleCard title="TODOs">
          <p className="text-sm text-[var(--color-muted-foreground)]">
            {todos.length === 0 ? "Empty — reserved for future task extraction." : null}
          </p>
        </CollapsibleCard>
      </div>
    </div>
  );
}
