import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { conversationBranchSchema, type ConversationBranchForm } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface BranchConversationDialogProps {
  conversationId: string;
  messageId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BranchConversationDialog({
  conversationId,
  messageId,
  open,
  onOpenChange,
}: BranchConversationDialogProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { activeWorkspaceId } = useWorkspace();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConversationBranchForm>({
    resolver: zodResolver(conversationBranchSchema),
    defaultValues: { branch_name: "" },
  });

  useEffect(() => {
    if (open) {
      reset({ branch_name: "" });
    }
  }, [open, reset]);

  const branchMutation = useMutation({
    mutationFn: (values: ConversationBranchForm) => {
      const trimmed = values.branch_name?.trim();
      return conversationApi.createBranch(conversationId, {
        message_id: messageId,
        branch_name: trimmed && trimmed.length > 0 ? trimmed : undefined,
      });
    },
    onSuccess: (branch) => {
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation-branches", conversationId] });
      toast.success("Branch created");
      onOpenChange(false);
      navigate(`/c/${branch.id}`);
    },
    onError: (error) => showApiError(error, "Unable to branch conversation"),
  });

  const onSubmit = handleSubmit(async (values) => {
    await branchMutation.mutateAsync(values);
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Branch from here</DialogTitle>
          <DialogDescription>
            Create a new conversation that starts from this message. The original conversation
            stays untouched.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="branch-name">Branch name (optional)</Label>
            <Input
              id="branch-name"
              placeholder="Experiment A"
              autoComplete="off"
              {...register("branch_name")}
            />
            {errors.branch_name && (
              <p className="text-sm text-[var(--color-destructive)]">{errors.branch_name.message}</p>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={branchMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={branchMutation.isPending}>
              {branchMutation.isPending ? "Creating..." : "Create branch"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
