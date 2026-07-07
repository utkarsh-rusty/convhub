import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { conversationApi, repositoryApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { CreateRepositoryDialog } from "@/components/repository/create-repository-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ConversationResponse } from "@/types/api";

type RepositoryMode = "existing" | "new" | "none";

interface EnableCodingDialogProps {
  conversation: ConversationResponse;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultRepositoryId?: string;
}

export function EnableCodingDialog({
  conversation,
  open,
  onOpenChange,
  defaultRepositoryId,
}: EnableCodingDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [repositoryMode, setRepositoryMode] = useState<RepositoryMode>(
    defaultRepositoryId ? "existing" : "none",
  );
  const [repositoryId, setRepositoryId] = useState(defaultRepositoryId ?? "");
  const [createRepositoryOpen, setCreateRepositoryOpen] = useState(false);

  const { data: repositories = [] } = useQuery({
    queryKey: ["repositories", activeWorkspaceId, conversation.project_id],
    queryFn: () => repositoryApi.list(conversation.project_id),
    enabled: Boolean(activeWorkspaceId && open),
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setRepositoryMode(defaultRepositoryId ? "existing" : repositories.length > 0 ? "existing" : "none");
    setRepositoryId(defaultRepositoryId ?? repositories[0]?.id ?? "");
  }, [open, defaultRepositoryId, repositories]);

  const enableMutation = useMutation({
    mutationFn: () => {
      if (repositoryMode === "existing" && repositoryId) {
        return conversationApi.enableCoding(conversation.id, {
          existing_repository_id: repositoryId,
        });
      }
      return conversationApi.enableCoding(conversation.id);
    },
    onSuccess: () => {
      toast.success("Coding workspace enabled");
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
      void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
      onOpenChange(false);
    },
    onError: (error) => showApiError(error, "Unable to enable coding workspace"),
  });

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Enable coding workspace</DialogTitle>
            <DialogDescription>
              Turn this conversation into a coding workspace. Optionally connect a repository now or
              attach one later.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-3 rounded-lg border border-[var(--color-border)] p-3">
              <Label>Repository (optional)</Label>
              <div className="space-y-2 text-sm">
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="enable-coding-repo-mode"
                    checked={repositoryMode === "none"}
                    onChange={() => setRepositoryMode("none")}
                  />
                  Enable without repository
                </label>
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="enable-coding-repo-mode"
                    checked={repositoryMode === "existing"}
                    onChange={() => setRepositoryMode("existing")}
                  />
                  Use existing repository
                </label>
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="enable-coding-repo-mode"
                    checked={repositoryMode === "new"}
                    onChange={() => setRepositoryMode("new")}
                  />
                  Create repository
                </label>
              </div>

              {repositoryMode === "existing" ? (
                repositories.length === 0 ? (
                  <p className="text-xs text-[var(--color-muted-foreground)]">
                    No repositories in this project yet.
                  </p>
                ) : (
                  <Select value={repositoryId} onValueChange={setRepositoryId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a repository" />
                    </SelectTrigger>
                    <SelectContent>
                      {repositories.map((repository) => (
                        <SelectItem key={repository.id} value={repository.id}>
                          {repository.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )
              ) : null}

              {repositoryMode === "new" ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCreateRepositoryOpen(true)}
                >
                  Create repository
                </Button>
              ) : null}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              disabled={
                enableMutation.isPending ||
                (repositoryMode === "existing" && repositories.length > 0 && !repositoryId)
              }
              onClick={() => enableMutation.mutate()}
            >
              {enableMutation.isPending ? "Enabling..." : "Enable coding"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <CreateRepositoryDialog
        open={createRepositoryOpen}
        onOpenChange={setCreateRepositoryOpen}
        projectId={conversation.project_id}
        onCreated={async (repository) => {
          await conversationApi.enableCoding(conversation.id, {
            existing_repository_id: repository.id,
          });
          toast.success("Coding workspace enabled");
          void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
          void queryClient.invalidateQueries({ queryKey: ["conversation", conversation.id] });
          void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
          onOpenChange(false);
        }}
      />
    </>
  );
}
