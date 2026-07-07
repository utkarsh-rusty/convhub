import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { conversationApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ConversationResponse } from "@/types/api";

interface DisableCodingDialogProps {
  conversation: ConversationResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DisableCodingDialog({
  conversation,
  open,
  onOpenChange,
}: DisableCodingDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const disableMutation = useMutation({
    mutationFn: () => conversationApi.disableCoding(conversation.id),
    onSuccess: () => {
      toast.success("Coding workspace disabled");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
      void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
      onOpenChange(false);
    },
    onError: (error) => showApiError(error, "Unable to disable coding workspace"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Disable coding workspace</DialogTitle>
          <DialogDescription>
            This detaches the repository from this conversation. Conversation history, commits,
            branches, context packages, and restore history remain intact.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={disableMutation.isPending}
            onClick={() => disableMutation.mutate()}
          >
            {disableMutation.isPending ? "Disabling..." : "Disable coding"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
