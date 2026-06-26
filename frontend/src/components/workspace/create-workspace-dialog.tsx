import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { workspaceApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { workspaceCreateSchema, type WorkspaceCreateForm } from "@/types/api";
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

export function CreateWorkspaceDialog() {
  const [open, setOpen] = useState(false);
  const { setActiveWorkspaceId, refetchWorkspaces } = useWorkspace();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<WorkspaceCreateForm>({
    resolver: zodResolver(workspaceCreateSchema),
  });

  const createMutation = useMutation({
    mutationFn: workspaceApi.create,
    onSuccess: (workspace) => {
      toast.success(`Created ${workspace.name}`);
      setActiveWorkspaceId(workspace.id);
      refetchWorkspaces();
      reset();
      setOpen(false);
    },
    onError: (error) => showApiError(error, "Unable to create workspace"),
  });

  const onSubmit = handleSubmit(async (values) => {
    await createMutation.mutateAsync(values);
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Create workspace">
          <Plus className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create workspace</DialogTitle>
          <DialogDescription>Add a new workspace for your team.</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="workspace-name">Name</Label>
            <Input id="workspace-name" placeholder="Acme Engineering" {...register("name")} />
            {errors.name && <p className="text-sm text-[var(--color-destructive)]">{errors.name.message}</p>}
          </div>
          <Button type="submit" className="w-full" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Creating..." : "Create workspace"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
