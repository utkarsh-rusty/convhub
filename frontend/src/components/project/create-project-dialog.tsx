import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { projectApi, showApiError } from "@/lib/api";
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
import { Textarea } from "@/components/ui/textarea";

interface CreateProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateProjectDialog({ open, onOpenChange }: CreateProjectDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState("#3b82f6");

  useEffect(() => {
    if (open) {
      setName("");
      setDescription("");
      setColor("#3b82f6");
    }
  }, [open]);

  const createMutation = useMutation({
    mutationFn: () =>
      projectApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
        color,
      }),
    onSuccess: (project) => {
      toast.success("Project created");
      void queryClient.invalidateQueries({ queryKey: ["projects", activeWorkspaceId] });
      onOpenChange(false);
      navigate(`/projects/${project.id}`);
    },
    onError: (error) => showApiError(error, "Unable to create project"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>
            Projects are the permanent home for conversations, commits, and context packages.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="project-name">Name</Label>
            <Input
              id="project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Backend"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-description">Description</Label>
            <Textarea
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional summary"
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-color">Color</Label>
            <Input
              id="project-color"
              type="color"
              value={color}
              onChange={(event) => setColor(event.target.value)}
              className="h-10 w-20 cursor-pointer p-1"
            />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!name.trim() || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? "Creating..." : "Create project"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
