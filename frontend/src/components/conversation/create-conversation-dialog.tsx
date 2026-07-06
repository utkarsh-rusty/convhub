import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { conversationApi, projectApi, showApiError } from "@/lib/api";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface CreateConversationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultProjectId?: string;
}

export function CreateConversationDialog({
  open,
  onOpenChange,
  defaultProjectId,
}: CreateConversationDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [title, setTitle] = useState("");
  const [projectId, setProjectId] = useState(defaultProjectId ?? "");

  const { data: projects = [] } = useQuery({
    queryKey: ["projects", activeWorkspaceId],
    queryFn: () => projectApi.list(),
    enabled: Boolean(activeWorkspaceId && open),
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setTitle("");
    const preferred =
      defaultProjectId ||
      projects.find((project) => project.is_default)?.id ||
      projects[0]?.id ||
      "";
    setProjectId(preferred);
  }, [open, defaultProjectId, projects]);

  const createMutation = useMutation({
    mutationFn: () =>
      conversationApi.create({
        title: title.trim() || undefined,
        project_id: projectId || undefined,
      }),
    onSuccess: (conversation) => {
      toast.success("Conversation created");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["projects", activeWorkspaceId] });
      onOpenChange(false);
      navigate(`/c/${conversation.id}`);
    },
    onError: (error) => showApiError(error, "Unable to create conversation"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New conversation</DialogTitle>
          <DialogDescription>Choose a project, then name the conversation.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Project</Label>
            <Select value={projectId} onValueChange={setProjectId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a project" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="conversation-name">Conversation name</Label>
            <Input
              id="conversation-name"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Untitled Conversation"
            />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={!projectId || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
