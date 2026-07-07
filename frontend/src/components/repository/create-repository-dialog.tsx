import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { repositoryApi, showApiError } from "@/lib/api";
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
import type { RepositoryProvider, RepositoryResponse, RepositoryVisibility } from "@/types/api";

interface CreateRepositoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onCreated?: (repository: RepositoryResponse) => void;
}

export function CreateRepositoryDialog({
  open,
  onOpenChange,
  projectId,
  onCreated,
}: CreateRepositoryDialogProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const [name, setName] = useState("");
  const [provider, setProvider] = useState<RepositoryProvider>("github");
  const [owner, setOwner] = useState("");
  const [repositoryName, setRepositoryName] = useState("");
  const [remoteUrl, setRemoteUrl] = useState("");
  const [defaultBranch, setDefaultBranch] = useState("main");
  const [visibility, setVisibility] = useState<RepositoryVisibility>("private");

  useEffect(() => {
    if (!open) {
      return;
    }
    setName("");
    setProvider("github");
    setOwner("");
    setRepositoryName("");
    setRemoteUrl("");
    setDefaultBranch("main");
    setVisibility("private");
  }, [open]);

  const createMutation = useMutation({
    mutationFn: () =>
      repositoryApi.create({
        project_id: projectId,
        name: name.trim(),
        provider,
        owner: owner.trim(),
        repository_name: repositoryName.trim(),
        remote_url: remoteUrl.trim(),
        default_branch: defaultBranch.trim() || "main",
        visibility,
      }),
    onSuccess: (repository) => {
      toast.success("Repository created");
      void queryClient.invalidateQueries({ queryKey: ["repositories", activeWorkspaceId] });
      void queryClient.invalidateQueries({ queryKey: ["projects", activeWorkspaceId] });
      onCreated?.(repository);
      onOpenChange(false);
    },
    onError: (error) => showApiError(error, "Unable to create repository"),
  });

  const canSubmit =
    Boolean(name.trim() && owner.trim() && repositoryName.trim() && remoteUrl.trim()) &&
    !createMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>New repository</DialogTitle>
          <DialogDescription>
            Register repository metadata for coding conversations. No Git connection in this sprint.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="repository-display-name">Display name</Label>
            <Input
              id="repository-display-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="ConvHub API"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Provider</Label>
              <Select value={provider} onValueChange={(value) => setProvider(value as RepositoryProvider)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="github">GitHub</SelectItem>
                  <SelectItem value="gitlab">GitLab</SelectItem>
                  <SelectItem value="bitbucket">Bitbucket</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Visibility</Label>
              <Select
                value={visibility}
                onValueChange={(value) => setVisibility(value as RepositoryVisibility)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">Private</SelectItem>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="repository-owner">Owner</Label>
              <Input
                id="repository-owner"
                value={owner}
                onChange={(event) => setOwner(event.target.value)}
                placeholder="convhub"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="repository-slug">Repository name</Label>
              <Input
                id="repository-slug"
                value={repositoryName}
                onChange={(event) => setRepositoryName(event.target.value)}
                placeholder="api"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="repository-remote-url">Remote URL</Label>
            <Input
              id="repository-remote-url"
              value={remoteUrl}
              onChange={(event) => setRemoteUrl(event.target.value)}
              placeholder="https://github.com/convhub/api"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="repository-default-branch">Default branch</Label>
            <Input
              id="repository-default-branch"
              value={defaultBranch}
              onChange={(event) => setDefaultBranch(event.target.value)}
              placeholder="main"
            />
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" disabled={!canSubmit} onClick={() => createMutation.mutate()}>
            {createMutation.isPending ? "Creating..." : "Create repository"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
