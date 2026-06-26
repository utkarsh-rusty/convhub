import { z } from "zod";

export const workspaceRoleSchema = z.enum(["owner", "admin", "member"]);
export const messageRoleSchema = z.enum(["user", "assistant", "system"]);
export const conversationParticipantRoleSchema = z.enum(["owner", "member"]);
export const aiProviderNameSchema = z.enum(["mock", "anthropic", "ollama"]);
export type AIProviderName = z.infer<typeof aiProviderNameSchema>;

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

export const workspaceMemberResponseSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
  role: workspaceRoleSchema,
  created_at: z.string(),
});

export const invitationCreateSchema = z.object({
  email: z.string().email("Enter a valid email"),
  role: workspaceRoleSchema,
});

export const invitationResponseSchema = z.object({
  token: z.string(),
  email: z.string().email(),
  role: workspaceRoleSchema,
  expires_at: z.string(),
});

export const acceptInvitationResponseSchema = z.object({
  workspace_id: z.string().uuid(),
  workspace_name: z.string(),
  role: workspaceRoleSchema,
});

export const conversationParticipantSummarySchema = z.object({
  user_id: z.string().uuid(),
  name: z.string(),
  role: conversationParticipantRoleSchema,
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
  participant_count: z.number().default(0),
  participants: z.array(conversationParticipantSummarySchema).default([]),
});

export const conversationParticipantResponseSchema = z.object({
  conversation_id: z.string().uuid(),
  user_id: z.string().uuid(),
  name: z.string(),
  email: z.string().email(),
  role: conversationParticipantRoleSchema,
  joined_at: z.string(),
});

export const messageResponseSchema = z.object({
  id: z.string().uuid(),
  conversation_id: z.string().uuid(),
  author_id: z.string().uuid().nullable(),
  role: messageRoleSchema,
  content: z.string(),
  created_at: z.string(),
  provider: z.string().nullable().optional(),
});

export const aiAccountResponseSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  provider: z.string(),
  display_name: z.string(),
  is_active: z.boolean(),
  monthly_budget: z.string().nullable(),
  monthly_spent: z.string(),
  priority: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const aiAccountTestResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

export const budgetResponseSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  user_id: z.string().uuid(),
  monthly_credit_limit: z.string(),
  used_credits: z.string(),
  borrowed_credits: z.string(),
  lent_credits: z.string(),
  remaining_credits: z.string(),
  reset_date: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const creditTransactionResponseSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  request_id: z.string().uuid().nullable(),
  from_user_id: z.string().uuid().nullable(),
  to_user_id: z.string().uuid().nullable(),
  transaction_type: z.enum(["allocation", "usage", "borrow", "lend", "adjustment"]),
  amount: z.string(),
  description: z.string(),
  created_at: z.string(),
});

export const creditTransactionListResponseSchema = z.object({
  items: z.array(creditTransactionResponseSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const routingPolicyTypeSchema = z.enum([
  "owner_first",
  "balanced",
  "lowest_usage",
  "cheapest",
  "priority",
]);

export const routingPreviewSchema = z.object({
  selected_account_id: z.string().uuid().nullable(),
  selected_provider: z.string(),
  selected_model: z.string(),
  policy_used: routingPolicyTypeSchema,
  routing_policy: routingPolicyTypeSchema,
  score: z.string().nullable(),
  decision_reason: z.string(),
});

export const routingSettingsResponseSchema = z.object({
  routing_policy: routingPolicyTypeSchema,
  active_accounts: z.array(
    z.object({
      id: z.string().uuid(),
      provider: z.string(),
      display_name: z.string(),
      is_active: z.boolean(),
      priority: z.number(),
      monthly_spent: z.string(),
      default_model: z.string().nullable(),
    }),
  ),
  preview: routingPreviewSchema,
});

export const lendingPreferenceResponseSchema = z.object({
  workspace_id: z.string().uuid(),
  user_id: z.string().uuid(),
  auto_share_enabled: z.boolean(),
  monthly_share_limit: z.string(),
  minimum_reserved_credits: z.string(),
  priority: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const workspaceSharingMemberSchema = z.object({
  user_id: z.string().uuid(),
  user_name: z.string(),
  user_email: z.string(),
  auto_share_enabled: z.boolean(),
  remaining_credits: z.string(),
  monthly_share_limit: z.string(),
  minimum_reserved_credits: z.string(),
  borrowed_credits: z.string(),
  lent_credits: z.string(),
  priority: z.number(),
});

export const workspaceSharingOverviewSchema = z.object({
  members: z.array(workspaceSharingMemberSchema),
});

export type TokenResponse = z.infer<typeof tokenResponseSchema>;
export type UserResponse = z.infer<typeof userResponseSchema>;
export type WorkspaceResponse = z.infer<typeof workspaceResponseSchema>;
export type WorkspaceMemberResponse = z.infer<typeof workspaceMemberResponseSchema>;
export type InvitationResponse = z.infer<typeof invitationResponseSchema>;
export type ConversationResponse = z.infer<typeof conversationResponseSchema>;
export type ConversationParticipantSummary = z.infer<typeof conversationParticipantSummarySchema>;
export type ConversationParticipantResponse = z.infer<typeof conversationParticipantResponseSchema>;
export type MessageResponse = z.infer<typeof messageResponseSchema>;
export type AIAccountResponse = z.infer<typeof aiAccountResponseSchema>;
export type BudgetResponse = z.infer<typeof budgetResponseSchema>;
export type CreditTransactionResponse = z.infer<typeof creditTransactionResponseSchema>;
export type RoutingPolicyType = z.infer<typeof routingPolicyTypeSchema>;
export type RoutingSettingsResponse = z.infer<typeof routingSettingsResponseSchema>;
export type LendingPreferenceResponse = z.infer<typeof lendingPreferenceResponseSchema>;
export type WorkspaceSharingOverview = z.infer<typeof workspaceSharingOverviewSchema>;

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

export const aiAccountCreateSchema = z
  .object({
    provider: aiProviderNameSchema,
    display_name: z.string().min(1, "Display name is required").max(255),
    api_key: z.string().optional(),
    is_active: z.boolean(),
    priority: z.number().int().min(0),
  })
  .superRefine((data, ctx) => {
    if (data.provider !== "ollama" && !data.api_key?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "API key is required",
        path: ["api_key"],
      });
    }
  });

export type LoginForm = z.infer<typeof loginSchema>;
export type RegisterForm = z.infer<typeof registerSchema>;
export type WorkspaceCreateForm = z.infer<typeof workspaceCreateSchema>;
export type ConversationUpdateForm = z.infer<typeof conversationUpdateSchema>;
export type MessageCreateForm = z.infer<typeof messageCreateSchema>;
export type AIAccountCreateForm = z.infer<typeof aiAccountCreateSchema>;
export type InvitationCreateForm = z.infer<typeof invitationCreateSchema>;
