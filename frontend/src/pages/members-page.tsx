import { useQuery } from "@tanstack/react-query";

import { workspaceApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { InviteMemberDialog } from "@/components/workspace/invite-member-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { getInitials } from "@/lib/utils";

export function MembersPage() {
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const canInvite = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["workspace-members", activeWorkspaceId],
    queryFn: () => workspaceApi.listMembers(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId),
  });

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to view members.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">Members</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            People in {activeWorkspace?.name ?? "this workspace"}
          </p>
        </div>
        {canInvite && <InviteMemberDialog />}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-14 w-full" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3"
              >
                <Avatar>
                  <AvatarFallback>{getInitials(member.name)}</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{member.name}</p>
                  <p className="text-sm text-[var(--color-muted-foreground)]">{member.email}</p>
                </div>
                <span className="rounded-full bg-[var(--color-accent)] px-2 py-1 text-xs capitalize">
                  {member.role}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
