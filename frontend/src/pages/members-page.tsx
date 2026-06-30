import { useMutation, useQuery } from "@tanstack/react-query";
import { Copy } from "lucide-react";
import { toast } from "sonner";

import { workspaceApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { InviteMemberDialog } from "@/components/workspace/invite-member-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
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

  const { data: pendingInvites = [], isLoading: invitesLoading } = useQuery({
    queryKey: ["pending-invitations", activeWorkspaceId],
    queryFn: () => workspaceApi.listPendingInvitations(activeWorkspaceId!),
    enabled: Boolean(activeWorkspaceId && canInvite),
  });

  const copyLinkMutation = useMutation({
    mutationFn: (invitationId: string) =>
      workspaceApi.refreshInvitationLink(activeWorkspaceId!, invitationId),
    onSuccess: async (invitation) => {
      const link = `${window.location.origin}/invite/${invitation.token}`;
      await navigator.clipboard.writeText(link);
      toast.success(`Invite link copied for ${invitation.email}`);
    },
    onError: (error) => showApiError(error, "Unable to copy invite link"),
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

      <div className="flex-1 space-y-8 overflow-y-auto px-6 py-6">
        <section>
          <h3 className="mb-3 text-sm font-medium">Active members</h3>
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
        </section>

        {canInvite && (
          <section>
            <h3 className="mb-3 text-sm font-medium">Pending invitations</h3>
            {invitesLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : pendingInvites.length === 0 ? (
              <p className="text-sm text-[var(--color-muted-foreground)]">No pending invitations.</p>
            ) : (
              <div className="space-y-2">
                {pendingInvites.map((invite) => (
                  <div
                    key={invite.id}
                    className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-3"
                  >
                    <div>
                      <p className="font-medium">{invite.email}</p>
                      <p className="text-sm text-[var(--color-muted-foreground)] capitalize">
                        {invite.role} · expires {new Date(invite.expires_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={copyLinkMutation.isPending}
                      onClick={() => copyLinkMutation.mutate(invite.id)}
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copy link
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
