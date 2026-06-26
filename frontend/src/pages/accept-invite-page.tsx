import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { invitationApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function AcceptInvitePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setActiveWorkspaceId } = useWorkspace();

  const acceptMutation = useMutation({
    mutationFn: () => invitationApi.accept(token!),
    onSuccess: async (result) => {
      toast.success(`Joined ${result.workspace_name}`);
      setActiveWorkspaceId(result.workspace_id);
      await queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      navigate("/", { replace: true });
    },
    onError: (error) => showApiError(error, "Unable to accept invitation"),
  });

  if (!token) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Invalid invitation link.
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <div className="w-full max-w-md space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-center">
        <h2 className="text-lg font-semibold">Workspace invitation</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Accept this invitation to join the shared workspace.
        </p>
        {acceptMutation.isPending ? (
          <Skeleton className="mx-auto h-10 w-40" />
        ) : (
          <Button onClick={() => acceptMutation.mutate()} disabled={acceptMutation.isSuccess}>
            Join workspace
          </Button>
        )}
      </div>
    </div>
  );
}
