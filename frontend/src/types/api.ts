import { z } from "zod";

export const workspaceRoleSchema = z.enum(["owner", "admin", "member"]);
export const messageRoleSchema = z.enum(["user", "assistant", "system"]);

export const tokenResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
});

export const userResponseSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
  created_at: z.string(),
});

export const workspaceResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  slug: z.string(),
  owner_id: z.string().uuid(),
  role: workspaceRoleSchema,
  created_at: z.string(),
  updated_at: z.string(),
});

export const conversationResponseSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  created_by_id: z.string().uuid().nullable(),
  title: z.string(),
  last_activity_at: z.string(),
  archived_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const messageResponseSchema = z.object({
  id: z.string().uuid(),
  conversation_id: z.string().uuid(),
  author_id: z.string().uuid().nullable(),
  role: messageRoleSchema,
  content: z.string(),
  created_at: z.string(),
});

export type TokenResponse = z.infer<typeof tokenResponseSchema>;
export type UserResponse = z.infer<typeof userResponseSchema>;
export type WorkspaceResponse = z.infer<typeof workspaceResponseSchema>;
export type ConversationResponse = z.infer<typeof conversationResponseSchema>;
export type MessageResponse = z.infer<typeof messageResponseSchema>;

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const registerSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const workspaceCreateSchema = z.object({
  name: z.string().min(1, "Workspace name is required").max(255),
});

export const conversationUpdateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
});

export const messageCreateSchema = z.object({
  content: z.string().min(1, "Message cannot be empty"),
});

export type LoginForm = z.infer<typeof loginSchema>;
export type RegisterForm = z.infer<typeof registerSchema>;
export type WorkspaceCreateForm = z.infer<typeof workspaceCreateSchema>;
export type ConversationUpdateForm = z.infer<typeof conversationUpdateSchema>;
export type MessageCreateForm = z.infer<typeof messageCreateSchema>;
