import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { conversationApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { conversationUpdateSchema, type ConversationResponse, type ConversationUpdateForm } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface RenameConversationDialogProps {
  conversation: ConversationResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RenameConversationDialog({
  conversation,
  open,
  onOpenChange,
}: RenameConversationDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConversationUpdateForm>({
    resolver: zodResolver(conversationUpdateSchema),
    defaultValues: { title: conversation.title },
  });

  useEffect(() => {
    reset({ title: conversation.title });
  }, [conversation.title, reset]);

  const updateMutation = useMutation({
    mutationFn: (values: ConversationUpdateForm) =>
      conversationApi.update(conversation.id, values),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
      toast.success("Conversation renamed");
      onOpenChange(false);
    },
    onError: (error) => showApiError(error, "Unable to rename conversation"),
  });

  const onSubmit = handleSubmit(async (values) => {
    await updateMutation.mutateAsync(values);
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rename conversation</DialogTitle>
          <DialogDescription>Update the title shown in your sidebar.</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor={`rename-${conversation.id}`}>Title</Label>
            <Input id={`rename-${conversation.id}`} {...register("title")} />
            {errors.title && (
              <p className="text-sm text-[var(--color-destructive)]">{errors.title.message}</p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? "Saving..." : "Save changes"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
