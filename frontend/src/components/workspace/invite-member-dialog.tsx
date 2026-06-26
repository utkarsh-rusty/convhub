import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { toast } from "sonner";

import { workspaceApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { invitationCreateSchema, type InvitationCreateForm } from "@/types/api";
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
import { Label } from "@/components/ui/label";

export function InviteMemberDialog() {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [inviteLink, setInviteLink] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InvitationCreateForm>({
    resolver: zodResolver(invitationCreateSchema),
    defaultValues: { role: "member" },
  });

  const inviteMutation = useMutation({
    mutationFn: (values: InvitationCreateForm) =>
      workspaceApi.invite(activeWorkspaceId!, values),
    onSuccess: (invitation) => {
      const link = `${window.location.origin}/invite/${invitation.token}`;
      setInviteLink(link);
      toast.success(`Invitation created for ${invitation.email}`);
      void queryClient.invalidateQueries({ queryKey: ["workspace-members", activeWorkspaceId] });
    },
    onError: (error) => showApiError(error, "Unable to send invitation"),
  });

  const onSubmit = handleSubmit(async (values) => {
    setInviteLink(null);
    await inviteMutation.mutateAsync(values);
  });

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      reset();
      setInviteLink(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm">
          <UserPlus className="mr-2 h-4 w-4" />
          Invite member
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Invite to workspace</DialogTitle>
          <DialogDescription>
            Add someone by email. They must accept the invite before they appear in
            conversations.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="invite-email">Email</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="colleague@example.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-sm text-[var(--color-destructive)]">{errors.email.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={inviteMutation.isPending}>
            {inviteMutation.isPending ? "Creating invite..." : "Create invite link"}
          </Button>
        </form>

        {inviteLink && (
          <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-muted)]/30 p-3">
            <p className="text-sm font-medium">Share this link with them</p>
            <p className="break-all text-xs text-[var(--color-muted-foreground)]">{inviteLink}</p>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={async () => {
                await navigator.clipboard.writeText(inviteLink);
                toast.success("Invite link copied");
              }}
            >
              Copy link
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
