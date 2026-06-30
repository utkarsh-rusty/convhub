import { z } from "zod";

import { messageResponseSchema } from "@/types/api";

export const realtimeEventTypeSchema = z.enum([
  "message.created",
  "message.updated",
  "message.streaming",
  "message.completed",
  "typing.started",
  "typing.stopped",
  "conversation.updated",
  "credits.updated",
  "routing.selected",
  "borrow.started",
  "borrow.completed",
  "member.joined",
  "member.left",
  "notification.created",
  "presence.updated",
  "connected",
  "pong",
  "error",
]);

export const realtimeEventSchema = z.object({
  type: realtimeEventTypeSchema,
  timestamp: z.string(),
  workspace_id: z.string().uuid(),
  conversation_id: z.string().uuid().nullable(),
  payload: z.record(z.string(), z.unknown()),
});

export type RealtimeEvent = z.infer<typeof realtimeEventSchema>;
export type RealtimeEventType = z.infer<typeof realtimeEventTypeSchema>;

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "reconnecting";

export const streamingMessageSchema = z.object({
  stream_id: z.string(),
  provider: z.string(),
  model: z.string(),
  delta: z.string(),
  content: z.string(),
});

export const completedMessageSchema = messageResponseSchema;
