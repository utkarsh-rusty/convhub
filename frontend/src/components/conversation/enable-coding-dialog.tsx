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

interface EnableCodingDialogProps {
  conversation: ConversationResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EnableCodingDialog({
  conversation,
  open,
  onOpenChange,
}: EnableCodingDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const enableMutation = useMutation({
    mutationFn: () => conversationApi.enableCoding(conversation.id),
    onSuccess: () => {
      toast.success("Coding workspace enabled");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
      onOpenChange(false);
    },
    onError: (error) => showApiError(error, "Unable to enable coding workspace"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Enable coding workspace</DialogTitle>
          <DialogDescription>
            Turn this conversation into a local coding workspace. You can attach a repository later
            when you are ready.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={enableMutation.isPending}
            onClick={() => enableMutation.mutate()}
          >
            {enableMutation.isPending ? "Enabling..." : "Enable coding"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
