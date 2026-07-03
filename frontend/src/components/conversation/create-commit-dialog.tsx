import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const commitFormSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().max(2000).optional(),
});

type CommitForm = z.infer<typeof commitFormSchema>;

interface CreateCommitDialogProps {
  conversationId: string;
  latestMessageId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateCommitDialog({
  conversationId,
  latestMessageId,
  open,
  onOpenChange,
}: CreateCommitDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CommitForm>({
    resolver: zodResolver(commitFormSchema),
    defaultValues: { title: "", description: "" },
  });

  useEffect(() => {
    if (open) {
      reset({ title: "", description: "" });
    }
  }, [open, reset]);

  const commitMutation = useMutation({
    mutationFn: (values: CommitForm) =>
      conversationApi.createCommit(conversationId, {
        title: values.title,
        description: values.description?.trim() || undefined,
        latest_message_id: latestMessageId,
      }),
    onSuccess: (commit) => {
      toast.success("Commit created successfully.");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation-commits", conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
      onOpenChange(false);
      toast.message(`Commit ${commit.commit_hash}`);
    },
    onError: (error) => showApiError(error, "Unable to create commit"),
  });

  const onSubmit = handleSubmit(async (values) => {
    await commitMutation.mutateAsync(values);
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create commit</DialogTitle>
          <DialogDescription>
            Save an intentional milestone at the latest visible message.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="commit-title">Title</Label>
            <Input id="commit-title" placeholder="Authentication Complete" {...register("title")} />
            {errors.title ? (
              <p className="text-sm text-[var(--color-destructive)]">{errors.title.message}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="commit-description">Description (optional)</Label>
            <Input
              id="commit-description"
              placeholder="What changed in this milestone?"
              {...register("description")}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={commitMutation.isPending}>
              {commitMutation.isPending ? "Committing..." : "Commit"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
