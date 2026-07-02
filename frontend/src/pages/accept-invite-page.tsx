import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { invitationApi, showApiError } from "@/lib/api";
import { APP_HOME } from "@/lib/site";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function AcceptInvitePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setActiveWorkspaceId } = useWorkspace();

  const { data: preview, isLoading } = useQuery({
    queryKey: ["invitation-preview", token],
    queryFn: () => invitationApi.preview(token!),
    enabled: Boolean(token),
  });

  const acceptMutation = useMutation({
    mutationFn: () => invitationApi.accept(token!),
    onSuccess: async (result) => {
      toast.success(`Joined ${result.workspace_name}`);
      setActiveWorkspaceId(result.workspace_id);
      await queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      navigate(APP_HOME, { replace: true });
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

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center px-6">
        <Skeleton className="h-40 w-full max-w-md" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <div className="w-full max-w-md space-y-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-center">
        <h2 className="text-lg font-semibold">Join {preview?.workspace_name ?? "workspace"}</h2>
        {preview?.is_valid ? (
          <>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              You&apos;ve been invited as <span className="capitalize">{preview.role}</span>.
            </p>
            <p className="text-xs text-[var(--color-muted-foreground)]">
              Invitation for {preview.email} · expires{" "}
              {new Date(preview.expires_at).toLocaleString()}
            </p>
            <Button
              onClick={() => acceptMutation.mutate()}
              disabled={acceptMutation.isPending || acceptMutation.isSuccess}
            >
              {acceptMutation.isPending ? "Joining..." : "Accept invitation"}
            </Button>
          </>
        ) : (
          <p className="text-sm text-[var(--color-destructive)]">
            This invitation is invalid, expired, or has already been used.
          </p>
        )}
      </div>
    </div>
  );
}
