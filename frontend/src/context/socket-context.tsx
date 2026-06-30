import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { RealtimeClient } from "@/lib/realtime";
import type { ConnectionStatus, RealtimeEvent } from "@/types/realtime";

type SocketContextValue = {
  status: ConnectionStatus;
  subscribeConversation: (conversationId: string) => void;
  unsubscribeConversation: (conversationId: string) => void;
  sendTyping: (conversationId: string, started: boolean) => void;
  onEvent: (handler: (event: RealtimeEvent) => void) => () => void;
};

const SocketContext = createContext<SocketContextValue | null>(null);

export function SocketProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { activeWorkspaceId } = useWorkspace();
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const clientRef = useRef<RealtimeClient | null>(null);
  const conversationsRef = useRef<Set<string>>(new Set());
  const handlersRef = useRef(new Set<(event: RealtimeEvent) => void>());

  useEffect(() => {
    if (!isAuthenticated || !activeWorkspaceId) {
      clientRef.current?.disconnect();
      clientRef.current = null;
      setStatus("disconnected");
      return;
    }

    const client = new RealtimeClient(setStatus);
    clientRef.current = client;
    conversationsRef.current = new Set();
    const unsubscribe = client.onMessage((event) => {
      handlersRef.current.forEach((handler) => handler(event));
    });
    client.connect(activeWorkspaceId, []);

    return () => {
      unsubscribe();
      client.disconnect();
      clientRef.current = null;
    };
  }, [isAuthenticated, activeWorkspaceId]);

  const syncSubscriptions = useCallback(() => {
    clientRef.current?.subscribe(Array.from(conversationsRef.current));
  }, []);

  const subscribeConversation = useCallback(
    (conversationId: string) => {
      conversationsRef.current.add(conversationId);
      syncSubscriptions();
    },
    [syncSubscriptions],
  );

  const unsubscribeConversation = useCallback(
    (conversationId: string) => {
      conversationsRef.current.delete(conversationId);
      syncSubscriptions();
    },
    [syncSubscriptions],
  );

  const sendTyping = useCallback((conversationId: string, started: boolean) => {
    clientRef.current?.sendTyping(conversationId, started);
  }, []);

  const onEvent = useCallback((handler: (event: RealtimeEvent) => void) => {
    handlersRef.current.add(handler);
    return () => {
      handlersRef.current.delete(handler);
    };
  }, []);

  const value = useMemo(
    () => ({
      status,
      subscribeConversation,
      unsubscribeConversation,
      sendTyping,
      onEvent,
    }),
    [status, subscribeConversation, unsubscribeConversation, sendTyping, onEvent],
  );

  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>;
}

export function useSocket() {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error("useSocket must be used within SocketProvider");
  }
  return context;
}
