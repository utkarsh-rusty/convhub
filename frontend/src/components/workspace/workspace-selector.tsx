import { useWorkspace } from "@/context/workspace-context";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export function WorkspaceSelector() {
  const { workspaces, activeWorkspaceId, isLoading, setActiveWorkspaceId } = useWorkspace();

  if (isLoading) {
    return <Skeleton className="h-9 w-full" />;
  }

  if (!workspaces.length) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-muted-foreground)]">
        No workspaces yet. Create one to get started.
      </div>
    );
  }

  return (
    <Select value={activeWorkspaceId ?? undefined} onValueChange={setActiveWorkspaceId}>
      <SelectTrigger>
        <SelectValue placeholder="Select workspace" />
      </SelectTrigger>
      <SelectContent>
        {workspaces.map((workspace) => (
          <SelectItem key={workspace.id} value={workspace.id}>
            {workspace.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
