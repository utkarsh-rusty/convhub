import { authStorage } from "@/lib/auth-storage";
import { realtimeEventSchema, type RealtimeEvent } from "@/types/realtime";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export function buildRealtimeUrl(token: string): string {
  const httpUrl = new URL(API_URL);
  const protocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${httpUrl.host}${httpUrl.pathname}/realtime/ws?token=${encodeURIComponent(token)}`;
}

export type RealtimeMessageHandler = (event: RealtimeEvent) => void;

export class RealtimeClient {
  private socket: WebSocket | null = null;
  private handlers = new Set<RealtimeMessageHandler>();
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private shouldReconnect = true;
  private workspaceId: string | null = null;
  private conversationIds: string[] = [];

  constructor(
    private readonly onStatusChange: (status: "connecting" | "connected" | "disconnected" | "reconnecting") => void,
  ) {}

  connect(workspaceId: string, conversationIds: string[] = []) {
    this.workspaceId = workspaceId;
    this.conversationIds = conversationIds;
    this.shouldReconnect = true;
    this.openSocket();
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
    this.onStatusChange("disconnected");
  }

  subscribe(conversationIds: string[]) {
    this.conversationIds = conversationIds;
    this.send({
      action: "subscribe",
      workspace_id: this.workspaceId,
      conversation_ids: conversationIds,
    });
  }

  sendTyping(conversationId: string, started: boolean) {
    this.send({
      action: started ? "typing.started" : "typing.stopped",
      conversation_id: conversationId,
    });
  }

  onMessage(handler: RealtimeMessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private openSocket() {
    const token = authStorage.getAccessToken();
    if (!token || !this.workspaceId) {
      return;
    }

    this.onStatusChange(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");
    const socket = new WebSocket(buildRealtimeUrl(token));
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStatusChange("connected");
      this.send({
        action: "subscribe",
        workspace_id: this.workspaceId,
        conversation_ids: this.conversationIds,
      });
    };

    socket.onmessage = (message) => {
      try {
        const parsed = realtimeEventSchema.parse(JSON.parse(message.data as string));
        for (const handler of this.handlers) {
          handler(parsed);
        }
      } catch {
        // Ignore malformed events.
      }
    };

    socket.onclose = () => {
      this.socket = null;
      if (!this.shouldReconnect) {
        this.onStatusChange("disconnected");
        return;
      }
      this.onStatusChange("reconnecting");
      const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000);
      this.reconnectAttempts += 1;
      this.reconnectTimer = window.setTimeout(() => this.openSocket(), delay);
    };
  }

  private send(payload: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }
}
