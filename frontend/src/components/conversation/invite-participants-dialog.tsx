import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, UserPlus } from "lucide-react";
import { toast } from "sonner";

import { conversationApi, showApiError, workspaceApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn, getInitials } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface InviteParticipantsDialogProps {
  conversationId: string;
  participantUserIds: string[];
}

export function InviteParticipantsDialog({
  conversationId,
  participantUserIds,
}: InviteParticipantsDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["workspace-members", activeWorkspaceId],
    queryFn: () => workspaceApi.listMembers(activeWorkspaceId!),
    enabled: Boolean(open && activeWorkspaceId),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      conversationApi.addParticipants(conversationId, { user_ids: selectedIds }),
    onSuccess: () => {
      toast.success("Participants invited");
      setSelectedIds([]);
      setSearch("");
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["participants", conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
    },
    onError: (error) => showApiError(error, "Unable to invite participants"),
  });

  const availableMembers = useMemo(() => {
    const participantSet = new Set(participantUserIds);
    return members
      .filter((member) => !participantSet.has(member.user_id))
      .filter((member) => {
        const query = search.trim().toLowerCase();
        if (!query) {
          return true;
        }
        return (
          member.name.toLowerCase().includes(query) ||
          member.email.toLowerCase().includes(query)
        );
      });
  }, [members, participantUserIds, search]);

  const toggleMember = (userId: string) => {
    setSelectedIds((current) =>
      current.includes(userId) ? current.filter((id) => id !== userId) : [...current, userId],
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <UserPlus className="mr-2 h-4 w-4" />
          Invite
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Invite participants</DialogTitle>
          <DialogDescription>
            Search workspace members and add them to this conversation.
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-muted-foreground)]" />
          <Input
            className="pl-9"
            placeholder="Search by name or email"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="max-h-64 space-y-1 overflow-y-auto rounded-md border border-[var(--color-border)] p-2">
          {isLoading ? (
            <p className="px-2 py-4 text-sm text-[var(--color-muted-foreground)]">Loading members...</p>
          ) : availableMembers.length === 0 ? (
            <p className="px-2 py-4 text-sm text-[var(--color-muted-foreground)]">
              No other workspace members to invite. Add them to this workspace first from the
              Members page.
            </p>
          ) : (
            availableMembers.map((member) => {
              const selected = selectedIds.includes(member.user_id);
              return (
                <button
                  key={member.user_id}
                  type="button"
                  onClick={() => toggleMember(member.user_id)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors",
                    selected
                      ? "bg-[var(--color-accent)]"
                      : "hover:bg-[var(--color-muted)]/40",
                  )}
                >
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>{getInitials(member.name)}</AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{member.name}</p>
                    <p className="truncate text-xs text-[var(--color-muted-foreground)]">
                      {member.email}
                    </p>
                  </div>
                  <span className="text-xs capitalize text-[var(--color-muted-foreground)]">
                    {member.role}
                  </span>
                </button>
              );
            })
          )}
        </div>

        <Button
          className="w-full"
          disabled={selectedIds.length === 0 || inviteMutation.isPending}
          onClick={() => inviteMutation.mutate()}
        >
          {inviteMutation.isPending
            ? "Inviting..."
            : `Invite ${selectedIds.length || ""} member${selectedIds.length === 1 ? "" : "s"}`}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
