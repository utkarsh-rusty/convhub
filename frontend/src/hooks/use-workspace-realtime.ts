import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useSocket } from "@/context/socket-context";
import { useWorkspace } from "@/context/workspace-context";

export function useWorkspaceRealtime() {
  const { onEvent } = useSocket();
  const { activeWorkspaceId } = useWorkspace();
  const queryClient = useQueryClient();
  const [presence, setPresence] = useState<Record<string, { name: string; status: string }>>({});

  useEffect(() => {
    if (!activeWorkspaceId) {
      return;
    }

    return onEvent((event) => {
      if (event.workspace_id !== activeWorkspaceId) {
        return;
      }

      if (event.type === "presence.updated") {
        const userId = String(event.payload.user_id ?? "");
        const userName = String(event.payload.user_name ?? "Member");
        const status = String(event.payload.status ?? "offline");
        if (!userId) {
          return;
        }
        setPresence((current) => ({
          ...current,
          [userId]: { name: userName, status },
        }));
        return;
      }

      if (event.type === "credits.updated") {
        void queryClient.invalidateQueries({ queryKey: ["budget", activeWorkspaceId] });
        void queryClient.invalidateQueries({ queryKey: ["credit-history", activeWorkspaceId] });
        void queryClient.invalidateQueries({ queryKey: ["workspace-budget-settings", activeWorkspaceId] });
        void queryClient.invalidateQueries({ queryKey: ["sharing-overview", activeWorkspaceId] });
        void queryClient.invalidateQueries({ queryKey: ["demo-budgets", activeWorkspaceId] });
        return;
      }

      if (event.type === "routing.selected" || event.type === "borrow.started" || event.type === "borrow.completed") {
        void queryClient.invalidateQueries({ queryKey: ["routing-settings", activeWorkspaceId] });
        void queryClient.invalidateQueries({ queryKey: ["sharing-overview", activeWorkspaceId] });
        return;
      }

      if (event.type === "conversation.updated") {
        void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
      }
    });
  }, [activeWorkspaceId, onEvent, queryClient]);

  return useMemo(() => ({ presence }), [presence]);
}
