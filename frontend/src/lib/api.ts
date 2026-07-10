import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { toast } from "sonner";
import { z } from "zod";

import { authStorage } from "@/lib/auth-storage";
import {
  aiAccountResponseSchema,
  aiAccountTestResponseSchema,
  budgetResponseSchema,
  creditTransactionListResponseSchema,
  routingSettingsResponseSchema,
  demoConfigResponseSchema,
  demoLoginResponseSchema,
  demoUsersResponseSchema,
  systemStatusResponseSchema,
  demoEventResponseSchema,
  demoSettingsResponseSchema,
  demoUserBudgetSummarySchema,
  lendingPreferenceResponseSchema,
  workspaceSharingOverviewSchema,
  invitationResponseSchema,
  acceptInvitationResponseSchema,
  pendingInvitationResponseSchema,
  invitationPreviewResponseSchema,
  workspaceBudgetSettingsSchema,
  branchFamilyOverviewResponseSchema,
  branchManagerResponseSchema,
  branchTreeResponseSchema,
  commitDetailResponseSchema,
  commitGraphResponseSchema,
  commitListItemSchema,
  commitSearchResponseSchema,
  contextPackageExportResponseSchema,
  contextPackageListItemSchema,
  contextPackageResponseSchema,
  conversationRestoreInfoResponseSchema,
  conversationCompareResponseSchema,
  conversationLineageResponseSchema,
  conversationParticipantResponseSchema,
  conversationResponseSchema,
  projectResponseSchema,
  repositoryResponseSchema,
  repositoryBranchResponseSchema,
  branchMemoryExportResponseSchema,
  branchSyncHistoryExportResponseSchema,
  branchSyncRecordSummarySchema,
  syncPullResponseSchema,
  syncPushResponseSchema,
  syncStatusResponseSchema,
  conversationSearchResponseSchema,
  conversationStatsResponseSchema,
  conversationTimelineResponseSchema,
  messageResponseSchema,
  tokenResponseSchema,
  userResponseSchema,
  workspaceMemberResponseSchema,
  workspaceResponseSchema,
  type AIAccountResponse,
  type AIProviderName,
  type BudgetResponse,
  type ConversationResponse,
  type MessageResponse,
  type TokenResponse,
  type UserResponse,
  type DemoSettingsResponse,
  type RoutingSettingsResponse,
  type WorkspaceResponse,
} from "@/types/api";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = authStorage.getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  try {
    const { data } = await axios.post<TokenResponse>(`${API_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    const tokens = tokenResponseSchema.parse(data);
    authStorage.setTokens(tokens.access_token, tokens.refresh_token);
    return tokens.access_token;
  } catch {
    authStorage.clearAll();
    return null;
  }
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const accessToken = authStorage.getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  const workspaceId = authStorage.getWorkspaceId();
  if (workspaceId) {
    config.headers["X-Workspace-ID"] = workspaceId;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string | { msg?: string }[] }>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });

      const newToken = await refreshPromise;
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      }

      if (!originalRequest.url?.includes("/auth/login") && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  },
);

export function getErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    const detailText =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : null;

    if (status === 402) {
      if (detailText?.toLowerCase().includes("insufficient credits")) {
        return "You have exhausted your monthly credits. Ask a teammate to share credits or wait for your next allocation.";
      }
      return "You have exhausted your monthly credits.";
    }

    if (status === 502 || detailText?.toLowerCase().includes("provider failed")) {
      return "All eligible AI accounts failed. Try another provider or check AI Providers.";
    }

    if (detailText) {
      const normalized = detailText.toLowerCase();
      if (normalized.includes("borrowing") && normalized.includes("disabled")) {
        return "Credit borrowing is disabled for this workspace. Enable it in Settings.";
      }
      if (normalized.includes("no eligible") && normalized.includes("sharing")) {
        return "No eligible teammates are sharing credits.";
      }
      if (normalized.includes("demo mode is not enabled")) {
        return "Demo mode is not enabled on this server.";
      }
      return detailText;
    }

    if (error.message) {
      return error.message;
    }
  }
  return fallback;
}

export function showApiError(error: unknown, fallback?: string) {
  toast.error(getErrorMessage(error, fallback));
}

export const authApi = {
  async login(payload: { email: string; password: string }) {
    const { data } = await api.post("/auth/login", payload);
    return tokenResponseSchema.parse(data);
  },

  async register(payload: { email: string; password: string; name: string }) {
    const { data } = await api.post("/auth/register", payload);
    return userResponseSchema.parse(data);
  },

  async me() {
    const { data } = await api.get("/users/me");
    return userResponseSchema.parse(data);
  },
};

export const workspaceApi = {
  async list() {
    const { data } = await api.get("/workspaces");
    return workspaceResponseSchema.array().parse(data);
  },

  async create(payload: { name: string }) {
    const { data } = await api.post("/workspaces", payload);
    return workspaceResponseSchema.parse(data);
  },

  async listMembers(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/members`);
    return workspaceMemberResponseSchema.array().parse(data);
  },

  async invite(
    workspaceId: string,
    payload: { email: string; role?: "owner" | "admin" | "member" },
  ) {
    const { data } = await api.post(`/workspaces/${workspaceId}/invite`, payload);
    return invitationResponseSchema.parse(data);
  },

  async listPendingInvitations(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/invitations`);
    return pendingInvitationResponseSchema.array().parse(data);
  },

  async refreshInvitationLink(workspaceId: string, invitationId: string) {
    const { data } = await api.post(
      `/workspaces/${workspaceId}/invitations/${invitationId}/link`,
    );
    return invitationResponseSchema.parse(data);
  },
};

export const invitationApi = {
  async preview(token: string) {
    const { data } = await axios.get(`${API_URL}/invitations/${token}`);
    return invitationPreviewResponseSchema.parse(data);
  },

  async accept(token: string) {
    const { data } = await api.post(`/invitations/${token}/accept`);
    return acceptInvitationResponseSchema.parse(data);
  },
};

export const projectApi = {
  async list(includeArchived = false) {
    const { data } = await api.get("/projects", {
      params: includeArchived ? { include_archived: true } : undefined,
    });
    return projectResponseSchema.array().parse(data);
  },

  async get(projectId: string) {
    const { data } = await api.get(`/projects/${projectId}`);
    return projectResponseSchema.parse(data);
  },

  async create(payload: {
    name: string;
    description?: string;
    icon?: string;
    color?: string;
  }) {
    const { data } = await api.post("/projects", payload);
    return projectResponseSchema.parse(data);
  },

  async update(
    projectId: string,
    payload: {
      name?: string;
      description?: string;
      icon?: string;
      color?: string;
    },
  ) {
    const { data } = await api.patch(`/projects/${projectId}`, payload);
    return projectResponseSchema.parse(data);
  },

  async archive(projectId: string) {
    const { data } = await api.post(`/projects/${projectId}/archive`);
    return projectResponseSchema.parse(data);
  },

  async restore(projectId: string) {
    const { data } = await api.post(`/projects/${projectId}/restore`);
    return projectResponseSchema.parse(data);
  },

  async delete(projectId: string) {
    await api.delete(`/projects/${projectId}`);
  },

  async listConversations(projectId: string) {
    const { data } = await api.get(`/projects/${projectId}/conversations`);
    return conversationResponseSchema.array().parse(data);
  },

  async listRepositories(projectId: string, includeArchived = false) {
    const { data } = await api.get(`/projects/${projectId}/repositories`, {
      params: includeArchived ? { include_archived: true } : undefined,
    });
    return repositoryResponseSchema.array().parse(data);
  },
};

export const repositoryApi = {
  async list(projectId?: string, includeArchived = false) {
    const { data } = await api.get("/repositories", {
      params: {
        ...(projectId ? { project_id: projectId } : {}),
        ...(includeArchived ? { include_archived: true } : {}),
      },
    });
    return repositoryResponseSchema.array().parse(data);
  },

  async get(repositoryId: string) {
    const { data } = await api.get(`/repositories/${repositoryId}`);
    return repositoryResponseSchema.parse(data);
  },

  async create(payload: {
    project_id: string;
    name: string;
    provider: string;
    owner: string;
    repository_name: string;
    remote_url: string;
    default_branch?: string;
    visibility?: string;
    is_active?: boolean;
  }) {
    const { data } = await api.post("/repositories", payload);
    return repositoryResponseSchema.parse(data);
  },

  async update(
    repositoryId: string,
    payload: {
      name?: string;
      provider?: string;
      owner?: string;
      repository_name?: string;
      remote_url?: string;
      default_branch?: string;
      visibility?: string;
      is_active?: boolean;
    },
  ) {
    const { data } = await api.patch(`/repositories/${repositoryId}`, payload);
    return repositoryResponseSchema.parse(data);
  },

  async archive(repositoryId: string) {
    const { data } = await api.post(`/repositories/${repositoryId}/archive`);
    return repositoryResponseSchema.parse(data);
  },

  async restore(repositoryId: string) {
    const { data } = await api.post(`/repositories/${repositoryId}/restore`);
    return repositoryResponseSchema.parse(data);
  },

  async delete(repositoryId: string) {
    await api.delete(`/repositories/${repositoryId}`);
  },

  async listConversations(repositoryId: string) {
    const { data } = await api.get(`/repositories/${repositoryId}/conversations`);
    return conversationResponseSchema.array().parse(data);
  },

  async listBranches(repositoryId: string, includeInactive = false) {
    const { data } = await api.get(`/repositories/${repositoryId}/branches`, {
      params: includeInactive ? { include_inactive: true } : undefined,
    });
    return repositoryBranchResponseSchema.array().parse(data);
  },

  async createBranch(repositoryId: string, payload: { name: string; is_default?: boolean }) {
    const { data } = await api.post(`/repositories/${repositoryId}/branches`, payload);
    return repositoryBranchResponseSchema.parse(data);
  },
};

export const repositoryBranchApi = {
  async get(branchId: string) {
    const { data } = await api.get(`/repository-branches/${branchId}`);
    return repositoryBranchResponseSchema.parse(data);
  },

  async rename(branchId: string, payload: { name: string }) {
    const { data } = await api.patch(`/repository-branches/${branchId}`, payload);
    return repositoryBranchResponseSchema.parse(data);
  },

  async archive(branchId: string) {
    const { data } = await api.post(`/repository-branches/${branchId}/archive`);
    return repositoryBranchResponseSchema.parse(data);
  },

  async restore(branchId: string) {
    const { data } = await api.post(`/repository-branches/${branchId}/restore`);
    return repositoryBranchResponseSchema.parse(data);
  },

  async delete(branchId: string) {
    await api.delete(`/repository-branches/${branchId}`);
  },

  async exportMemory(branchId: string) {
    const { data } = await api.get(`/repository-branches/${branchId}/memory/export`);
    return branchMemoryExportResponseSchema.parse(data);
  },

  async listHistory(branchId: string) {
    const { data } = await api.get(`/repository-branches/${branchId}/history`);
    return branchSyncRecordSummarySchema.array().parse(data);
  },

  async exportHistory(branchId: string) {
    const { data } = await api.get(`/repository-branches/${branchId}/history/export`);
    return branchSyncHistoryExportResponseSchema.parse(data);
  },

  async getSyncRecord(recordId: string) {
    const { data } = await api.get(`/branch-sync-records/${recordId}`);
    return branchSyncRecordSummarySchema.parse(data);
  },
};

export const syncApi = {
  async getStatus(repositoryBranchId: string) {
    const { data } = await api.get("/sync/status", {
      params: { repository_branch_id: repositoryBranchId },
    });
    return syncStatusResponseSchema.parse(data);
  },

  async pull(repositoryBranchId: string) {
    const { data } = await api.get("/sync/pull", {
      params: { repository_branch_id: repositoryBranchId },
    });
    return syncPullResponseSchema.parse(data);
  },

  async push(repositoryBranchId: string, payload: { notes?: string } = {}) {
    const { data } = await api.post("/sync/push", payload, {
      params: { repository_branch_id: repositoryBranchId },
    });
    return syncPushResponseSchema.parse(data);
  },
};

export const conversationApi = {
  async list() {
    const { data } = await api.get("/conversations");
    return conversationResponseSchema.array().parse(data);
  },

  async create(payload: { title?: string; project_id?: string } = {}) {
    const { data } = await api.post("/conversations", payload);
    return conversationResponseSchema.parse(data);
  },

  async enableCoding(conversationId: string) {
    const { data } = await api.post(`/conversations/${conversationId}/enable-coding`, {});
    return conversationResponseSchema.parse(data);
  },

  async disableCoding(conversationId: string) {
    const { data } = await api.post(`/conversations/${conversationId}/disable-coding`);
    return conversationResponseSchema.parse(data);
  },

  async attachRepository(
    conversationId: string,
    payload: {
      repository_id?: string;
      create_repository?: {
        name: string;
        provider: string;
        owner: string;
        repository_name: string;
        remote_url: string;
        default_branch?: string;
        visibility?: string;
        is_active?: boolean;
      };
    },
  ) {
    const { data } = await api.post(`/conversations/${conversationId}/attach-repository`, payload);
    return conversationResponseSchema.parse(data);
  },

  async detachRepository(conversationId: string) {
    const { data } = await api.post(`/conversations/${conversationId}/detach-repository`);
    return conversationResponseSchema.parse(data);
  },

  async get(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}`);
    return conversationResponseSchema.parse(data);
  },

  async update(conversationId: string, payload: { title: string }) {
    const { data } = await api.patch(`/conversations/${conversationId}`, payload);
    return conversationResponseSchema.parse(data);
  },

  async listParticipants(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/participants`);
    return conversationParticipantResponseSchema.array().parse(data);
  },

  async addParticipants(conversationId: string, payload: { user_ids: string[] }) {
    const { data } = await api.post(`/conversations/${conversationId}/participants`, payload);
    return conversationParticipantResponseSchema.array().parse(data);
  },

  async removeParticipant(conversationId: string, userId: string) {
    await api.delete(`/conversations/${conversationId}/participants/${userId}`);
  },

  async createBranch(
    conversationId: string,
    payload: { message_id: string; branch_name?: string },
  ) {
    const { data } = await api.post(`/conversations/${conversationId}/branch`, payload);
    return conversationResponseSchema.parse(data);
  },

  async listBranches(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/branches`);
    return conversationResponseSchema.array().parse(data);
  },

  async getLineage(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/lineage`);
    return conversationLineageResponseSchema.parse(data);
  },

  async getBranchTree(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/branch-tree`);
    return branchTreeResponseSchema.parse(data);
  },

  async getBranchManager(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/branch-manager`);
    return branchManagerResponseSchema.parse(data);
  },

  async getCommitGraph(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/commit-graph`);
    return commitGraphResponseSchema.parse(data);
  },

  async getFamilyOverview(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/family-overview`);
    return branchFamilyOverviewResponseSchema.parse(data);
  },

  async searchCommits(
    conversationId: string,
    params: {
      q?: string;
      author?: string;
      provider?: string;
      date_from?: string;
      date_to?: string;
    },
  ) {
    const { data } = await api.get(`/conversations/${conversationId}/commits/search`, { params });
    return commitSearchResponseSchema.parse(data);
  },


  async compare(leftId: string, rightId: string) {
    const { data } = await api.get(`/conversations/${leftId}/compare/${rightId}`);
    return conversationCompareResponseSchema.parse(data);
  },

  async getTimeline(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/timeline`);
    return conversationTimelineResponseSchema.parse(data);
  },

  async getStats(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/stats`);
    return conversationStatsResponseSchema.parse(data);
  },

  async search(conversationId: string, query: string) {
    const { data } = await api.get(`/conversations/${conversationId}/search`, {
      params: { q: query },
    });
    return conversationSearchResponseSchema.parse(data);
  },

  async createCommit(
    conversationId: string,
    payload: { title: string; description?: string; latest_message_id: string },
  ) {
    const { data } = await api.post(`/conversations/${conversationId}/commit`, payload);
    return commitDetailResponseSchema.parse(data);
  },

  async listCommits(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/commits`);
    return commitListItemSchema.array().parse(data);
  },

  async getCommit(commitHash: string) {
    const { data } = await api.get(`/commits/${commitHash}`);
    return commitDetailResponseSchema.parse(data);
  },

  async getContextPackage(packageId: string) {
    const { data } = await api.get(`/context-packages/${packageId}`);
    return contextPackageResponseSchema.parse(data);
  },

  async getCommitContextPackage(commitId: string) {
    const { data } = await api.get(`/commits/${commitId}/context-package`);
    return contextPackageResponseSchema.parse(data);
  },

  async listContextPackages(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/context-packages`);
    return contextPackageListItemSchema.array().parse(data);
  },

  async exportContextPackage(packageId: string) {
    const { data } = await api.get(`/context-packages/${packageId}/export`);
    return contextPackageExportResponseSchema.parse(data);
  },

  async restoreContextPackage(
    packageId: string,
    payload: {
      conversation_name?: string;
      project_id?: string;
      restore_participants?: boolean;
      restore_messages?: boolean;
      restore_metadata?: boolean;
      restore_only_self?: boolean;
    },
  ) {
    const { data } = await api.post(`/context-packages/${packageId}/restore`, payload);
    return conversationResponseSchema.parse(data);
  },

  async getRestoreInfo(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/restore-info`);
    return conversationRestoreInfoResponseSchema.parse(data);
  },
};

export const messageApi = {
  async list(conversationId: string) {
    const { data } = await api.get(`/conversations/${conversationId}/messages`);
    return messageResponseSchema.array().parse(data);
  },

  async create(conversationId: string, payload: { content: string; role: "user" }) {
    const { data } = await api.post(`/conversations/${conversationId}/messages`, payload);
    return messageResponseSchema.parse(data);
  },
};

export const chatApi = {
  async send(payload: { conversation_id: string; content: string }) {
    const { data } = await api.post("/chat/send", payload);
    return messageResponseSchema.parse(data);
  },
};

export const aiAccountApi = {
  async list() {
    const { data } = await api.get("/ai-accounts");
    return aiAccountResponseSchema.array().parse(data);
  },

  async create(payload: {
    provider: AIProviderName;
    display_name: string;
    api_key?: string;
    is_active?: boolean;
    priority?: number;
  }) {
    const { data } = await api.post("/ai-accounts", payload);
    return aiAccountResponseSchema.parse(data);
  },

  async remove(accountId: string) {
    await api.delete(`/ai-accounts/${accountId}`);
  },

  async test(accountId: string) {
    const { data } = await api.post(`/ai-accounts/${accountId}/test`);
    return aiAccountTestResponseSchema.parse(data);
  },
};

export const budgetApi = {
  async getMyBudget(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/budget/me`);
    return budgetResponseSchema.parse(data);
  },

  async getWorkspaceSettings(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/settings/budget`);
    return workspaceBudgetSettingsSchema.parse(data);
  },

  async updateWorkspaceSettings(
    workspaceId: string,
    payload: {
      allow_credit_borrowing?: boolean;
      allow_local_models?: boolean;
      hard_budget_enforcement?: boolean;
      monthly_default_credits?: string;
    },
  ) {
    const { data } = await api.patch(`/workspaces/${workspaceId}/settings/budget`, payload);
    return workspaceBudgetSettingsSchema.parse(data);
  },

  async listHistory(workspaceId: string, params?: { limit?: number; offset?: number }) {
    const { data } = await api.get(`/workspaces/${workspaceId}/credits/history`, { params });
    return creditTransactionListResponseSchema.parse(data);
  },
};

export const routingApi = {
  async getSettings(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/routing`);
    return routingSettingsResponseSchema.parse(data);
  },

  async updateSettings(workspaceId: string, routing_policy: RoutingSettingsResponse["routing_policy"]) {
    const { data } = await api.patch(`/workspaces/${workspaceId}/routing`, { routing_policy });
    return routingSettingsResponseSchema.parse(data);
  },
};

export const demoApi = {
  async getConfig() {
    const { data } = await api.get("/demo/config");
    return demoConfigResponseSchema.parse(data);
  },

  async listUsers() {
    const { data } = await api.get("/demo/users");
    return demoUsersResponseSchema.parse(data);
  },

  async login(persona: "alice" | "bob" | "charlie") {
    const { data } = await api.post("/demo/login", { persona });
    return demoLoginResponseSchema.parse(data);
  },

  async getSettings(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/demo`);
    return demoSettingsResponseSchema.parse(data);
  },

  async updatePricingProfile(workspaceId: string, pricing_profile: DemoSettingsResponse["pricing_profile"]) {
    const { data } = await api.patch(`/workspaces/${workspaceId}/demo/pricing-profile`, {
      pricing_profile,
    });
    return demoSettingsResponseSchema.parse(data);
  },

  async updateProviderSimulation(
    workspaceId: string,
    provider_simulation: DemoSettingsResponse["provider_simulation"],
  ) {
    const { data } = await api.patch(`/workspaces/${workspaceId}/demo/provider-simulation`, {
      provider_simulation,
    });
    return demoSettingsResponseSchema.parse(data);
  },

  async updateRoutingOverride(
    workspaceId: string,
    payload: {
      routing_override_mode: DemoSettingsResponse["routing_override_mode"];
      routing_override_account_id?: string | null;
    },
  ) {
    const { data } = await api.patch(`/workspaces/${workspaceId}/demo/routing-override`, payload);
    return demoSettingsResponseSchema.parse(data);
  },

  async listBudgets(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/demo/budgets`);
    return demoUserBudgetSummarySchema.array().parse(data);
  },

  async setUserCredits(workspaceId: string, user_id: string, remaining_credits: string) {
    const { data } = await api.post(`/workspaces/${workspaceId}/demo/credits/set`, {
      user_id,
      remaining_credits,
    });
    return z.object({ budget: demoUserBudgetSummarySchema }).parse(data);
  },

  async resetUserCredits(workspaceId: string, userId: string) {
    const { data } = await api.post(`/workspaces/${workspaceId}/demo/credits/reset-user`, null, {
      params: { user_id: userId },
    });
    return z.object({ budget: demoUserBudgetSummarySchema }).parse(data);
  },

  async resetAllCredits(workspaceId: string) {
    const { data } = await api.post(`/workspaces/${workspaceId}/demo/credits/reset-all`);
    return data as { message: string; affected_count: number | null };
  },

  async clearLedger(workspaceId: string) {
    const { data } = await api.post(`/workspaces/${workspaceId}/demo/ledger/clear`);
    return data as { message: string; affected_count: number | null };
  },

  async reseedAllocations(workspaceId: string) {
    const { data } = await api.post(`/workspaces/${workspaceId}/demo/reseed`);
    return data as { message: string; affected_count: number | null };
  },

  async listEvents(workspaceId: string, limit = 20) {
    const { data } = await api.get(`/workspaces/${workspaceId}/demo/events`, { params: { limit } });
    return z.object({ items: demoEventResponseSchema.array() }).parse(data).items;
  },
};

export const systemApi = {
  async getStatus() {
    const { data } = await api.get("/system");
    return systemStatusResponseSchema.parse(data);
  },
};

export const sharingApi = {
  async getMyPreferences(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/sharing/me`);
    return lendingPreferenceResponseSchema.parse(data);
  },

  async updateMyPreferences(
    workspaceId: string,
    payload: {
      auto_share_enabled?: boolean;
      monthly_share_limit?: string;
      minimum_reserved_credits?: string;
      priority?: number;
    },
  ) {
    const { data } = await api.patch(`/workspaces/${workspaceId}/sharing/me`, payload);
    return lendingPreferenceResponseSchema.parse(data);
  },

  async getWorkspaceOverview(workspaceId: string) {
    const { data } = await api.get(`/workspaces/${workspaceId}/sharing`);
    return workspaceSharingOverviewSchema.parse(data);
  },
};

export type { AIAccountResponse, BudgetResponse, ConversationResponse, MessageResponse, RoutingSettingsResponse, UserResponse, WorkspaceResponse };
