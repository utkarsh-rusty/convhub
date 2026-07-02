import { z } from "zod";

export const workspaceRoleSchema = z.enum(["owner", "admin", "member"]);
export const messageRoleSchema = z.enum(["user", "assistant", "system"]);
export const conversationParticipantRoleSchema = z.enum(["owner", "member"]);
export const aiProviderNameSchema = z.enum(["mock", "anthropic", "ollama", "openai", "gemini", "groq"]);
export type AIProviderName = z.infer<typeof aiProviderNameSchema>;

export const routingPolicyTypeSchema = z.enum([
  "owner_first",
  "balanced",
  "lowest_usage",
  "cheapest",
  "priority",
]);

export const pricingProfileTypeSchema = z.enum(["production", "demo", "free"]);
export const providerSimulationModeSchema = z.enum([
  "normal",
  "timeout",
  "unauthorized",
  "rate_limit",
  "server_error",
]);
export const routingOverrideModeSchema = z.enum([
  "normal",
  "first_account",
  "second_account",
  "random",
  "specific_account",
]);

export const demoConfigResponseSchema = z.object({
  enabled: z.boolean(),
});

export const demoPersonaSchema = z.enum(["alice", "bob", "charlie"]);
export type DemoPersona = z.infer<typeof demoPersonaSchema>;

export const demoUserResponseSchema = z.object({
  persona: demoPersonaSchema,
  name: z.string(),
  email: z.string().email(),
  role: z.string(),
});

export const demoUsersResponseSchema = z.object({
  workspace_slug: z.string(),
  users: demoUserResponseSchema.array(),
});

export const demoLoginResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
  workspace_id: z.string().uuid().nullable(),
  workspace_slug: z.string().nullable(),
});

export const systemComponentStatusSchema = z.object({
  name: z.string(),
  status: z.enum(["healthy", "unhealthy", "degraded"]),
  detail: z.string().nullable().optional(),
});

export const systemProviderHealthSchema = z.object({
  account_id: z.string().uuid(),
  provider: z.string(),
  model: z.string(),
  display_name: z.string(),
  healthy: z.boolean(),
  last_used_at: z.string().nullable(),
  request_count: z.number(),
  credits_used: z.coerce.string(),
});

export const systemStatusResponseSchema = z.object({
  environment: z.string(),
  demo_mode: z.boolean(),
  components: systemComponentStatusSchema.array(),
  providers: systemProviderHealthSchema.array(),
});

export type SystemStatusResponse = z.infer<typeof systemStatusResponseSchema>;

export const demoSettingsResponseSchema = z.object({
  workspace_id: z.string().uuid(),
  pricing_profile: pricingProfileTypeSchema,
  provider_simulation: providerSimulationModeSchema,
  routing_override_mode: routingOverrideModeSchema,
  routing_override_account_id: z.string().uuid().nullable(),
});

export const demoEventResponseSchema = z.object({
  id: z.string().uuid(),
  event_type: z.string(),
  message: z.string(),
  created_at: z.string(),
});

export const demoUserBudgetSummarySchema = z.object({
  user_id: z.string().uuid(),
  monthly_credit_limit: z.string(),
  remaining_credits: z.string(),
  used_credits: z.string(),
  borrowed_credits: z.string(),
  lent_credits: z.string(),
});

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

export const pendingInvitationResponseSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: workspaceRoleSchema,
  expires_at: z.string(),
  created_at: z.string(),
});

export const invitationPreviewResponseSchema = z.object({
  workspace_name: z.string(),
  email: z.string().email(),
  role: workspaceRoleSchema,
  expires_at: z.string(),
  is_valid: z.boolean(),
});

export const workspaceBudgetSettingsSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  monthly_default_credits: z.string(),
  allow_credit_borrowing: z.boolean(),
  allow_emergency_pool: z.boolean(),
  allow_local_models: z.boolean(),
  hard_budget_enforcement: z.boolean().optional().default(false),
  routing_policy: routingPolicyTypeSchema,
  created_at: z.string(),
  updated_at: z.string(),
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

export const executionSummarySchema = z.object({
  provider: z.string(),
  model: z.string(),
  owner_name: z.string().nullable().optional(),
  account_owner_name: z.string().nullable().optional(),
  execution_type: z
    .enum([
      "own_provider",
      "borrowed_provider",
      "local_model",
      "own_account",
      "participant_account",
      "borrowed",
    ])
    .transform((value) => {
      if (value === "own_account") return "own_provider" as const;
      if (value === "participant_account" || value === "borrowed") return "borrowed_provider" as const;
      return value;
    }),
  routing_policy: routingPolicyTypeSchema,
  borrowed_from: z.string().nullable().optional(),
  credits_borrowed_from: z.string().nullable().optional(),
}).transform((execution) => ({
  provider: execution.provider,
  model: execution.model,
  owner_name: execution.owner_name ?? execution.account_owner_name ?? null,
  execution_type: execution.execution_type,
  routing_policy: execution.routing_policy,
  borrowed_from: execution.borrowed_from ?? execution.credits_borrowed_from ?? null,
}));

export const messageResponseSchema = z.object({
  id: z.string().uuid(),
  conversation_id: z.string().uuid(),
  author_id: z.string().uuid().nullable(),
  role: messageRoleSchema,
  content: z.string(),
  created_at: z.string(),
  provider: z.string().nullable().optional(),
  execution: executionSummarySchema.nullable().optional(),
  budget_warning: z.string().nullable().optional(),
});

export const aiAccountResponseSchema = z.object({
  id: z.string().uuid(),
  workspace_id: z.string().uuid(),
  owner_user_id: z.string().uuid(),
  owner_name: z.string().nullable().optional(),
  is_mine: z.boolean().optional(),
  provider: z.string(),
  display_name: z.string(),
  is_active: z.boolean(),
  monthly_budget: z.string().nullable(),
  monthly_spent: z.string(),
  priority: z.number(),
  default_model: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  last_used_at: z.string().nullable().optional(),
  request_count: z.number().optional(),
  credits_used: z.string().optional(),
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
export type ExecutionSummary = z.infer<typeof executionSummarySchema>;
export type MessageResponse = z.infer<typeof messageResponseSchema>;
export type PendingInvitationResponse = z.infer<typeof pendingInvitationResponseSchema>;
export type InvitationPreviewResponse = z.infer<typeof invitationPreviewResponseSchema>;
export type WorkspaceBudgetSettings = z.infer<typeof workspaceBudgetSettingsSchema>;
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
    default_model: z.string().max(255).optional(),
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
export type PricingProfileType = z.infer<typeof pricingProfileTypeSchema>;
export type ProviderSimulationMode = z.infer<typeof providerSimulationModeSchema>;
export type RoutingOverrideMode = z.infer<typeof routingOverrideModeSchema>;
export type DemoSettingsResponse = z.infer<typeof demoSettingsResponseSchema>;
