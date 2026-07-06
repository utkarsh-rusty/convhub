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

interface RestoreContextDialogProps {
  packageId: string;
  defaultName?: string;
  defaultProjectId?: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RestoreContextDialog({
  packageId,
  defaultName = "",
  defaultProjectId,
  open,
  onOpenChange,
}: RestoreContextDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [conversationName, setConversationName] = useState(defaultName);
  const [projectId, setProjectId] = useState(defaultProjectId ?? "");
  const [restoreParticipants, setRestoreParticipants] = useState(true);
  const [restoreMessages, setRestoreMessages] = useState(true);
  const [restoreMetadata, setRestoreMetadata] = useState(true);
  const [restoreOnlySelf, setRestoreOnlySelf] = useState(false);

  const { data: projects = [] } = useQuery({
    queryKey: ["projects", activeWorkspaceId],
    queryFn: () => projectApi.list(),
    enabled: Boolean(activeWorkspaceId && open),
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setConversationName(defaultName);
    setProjectId(
      defaultProjectId ||
        projects.find((project) => project.is_default)?.id ||
        projects[0]?.id ||
        "",
    );
    setRestoreParticipants(true);
    setRestoreMessages(true);
    setRestoreMetadata(true);
    setRestoreOnlySelf(false);
  }, [open, defaultName, defaultProjectId, projects]);

  const restoreMutation = useMutation({
    mutationFn: () =>
      conversationApi.restoreContextPackage(packageId, {
        conversation_name: conversationName.trim() || undefined,
        project_id: projectId || undefined,
        restore_participants: restoreParticipants,
        restore_messages: restoreMessages,
        restore_metadata: restoreMetadata,
        restore_only_self: restoreOnlySelf,
      }),
    onSuccess: (conversation) => {
      toast.success("Context restored into a new conversation");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["projects", activeWorkspaceId] });
      onOpenChange(false);
      navigate(`/c/${conversation.id}`);
    },
    onError: (error) => showApiError(error, "Unable to restore context package"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Restore Context</DialogTitle>
          <DialogDescription>
            Creates a new working conversation from this immutable checkpoint. History is never
            modified.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="restore-name">Conversation name</Label>
            <Input
              id="restore-name"
              value={conversationName}
              onChange={(event) => setConversationName(event.target.value)}
              placeholder="Restored working copy"
            />
          </div>

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
                    {defaultProjectId && project.id === defaultProjectId
                      ? " (original)"
                      : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={restoreParticipants}
              onChange={(event) => setRestoreParticipants(event.target.checked)}
            />
            Restore participants
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={restoreMessages}
              onChange={(event) => setRestoreMessages(event.target.checked)}
            />
            Restore messages
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={restoreMetadata}
              onChange={(event) => setRestoreMetadata(event.target.checked)}
            />
            Restore metadata
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={restoreOnlySelf}
              onChange={(event) => setRestoreOnlySelf(event.target.checked)}
            />
            Restore only myself
          </label>
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={restoreMutation.isPending || !projectId}
            onClick={() => restoreMutation.mutate()}
          >
            {restoreMutation.isPending ? "Restoring..." : "Restore"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
