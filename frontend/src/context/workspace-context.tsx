import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { workspaceApi } from "@/lib/api";
import { authStorage } from "@/lib/auth-storage";
import type { WorkspaceResponse } from "@/types/api";

interface WorkspaceContextValue {
  workspaces: WorkspaceResponse[];
  activeWorkspace: WorkspaceResponse | undefined;
  activeWorkspaceId: string | null;
  isLoading: boolean;
  setActiveWorkspaceId: (workspaceId: string) => void;
  refetchWorkspaces: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<string | null>(
    authStorage.getWorkspaceId(),
  );

  const { data: workspaces = [], isLoading, refetch } = useQuery({
    queryKey: ["workspaces"],
    queryFn: workspaceApi.list,
  });

  useEffect(() => {
    if (!workspaces.length) {
      return;
    }

    const storedId = authStorage.getWorkspaceId();
    const validStored = workspaces.find((workspace) => workspace.id === storedId);
    if (validStored) {
      setActiveWorkspaceIdState(validStored.id);
      return;
    }

    const firstWorkspace = workspaces[0];
    authStorage.setWorkspaceId(firstWorkspace.id);
    setActiveWorkspaceIdState(firstWorkspace.id);
  }, [workspaces]);

  const setActiveWorkspaceId = (workspaceId: string) => {
    authStorage.setWorkspaceId(workspaceId);
    setActiveWorkspaceIdState(workspaceId);
  };

  const activeWorkspace = workspaces.find((workspace) => workspace.id === activeWorkspaceId);

  const value = useMemo(
    () => ({
      workspaces,
      activeWorkspace,
      activeWorkspaceId,
      isLoading,
      setActiveWorkspaceId,
      refetchWorkspaces: () => {
        void refetch();
      },
    }),
    [workspaces, activeWorkspace, activeWorkspaceId, isLoading, refetch],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return context;
}
