const ACCESS_TOKEN_KEY = "convhub_access_token";
const REFRESH_TOKEN_KEY = "convhub_refresh_token";
const WORKSPACE_ID_KEY = "convhub_workspace_id";

let memoryAccessToken: string | null = null;

export const authStorage = {
  getAccessToken(): string | null {
    if (memoryAccessToken) {
      return memoryAccessToken;
    }
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  },

  setAccessToken(token: string) {
    memoryAccessToken = token;
    sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setRefreshToken(token: string) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },

  setTokens(accessToken: string, refreshToken: string) {
    this.setAccessToken(accessToken);
    this.setRefreshToken(refreshToken);
  },

  clearTokens() {
    memoryAccessToken = null;
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  getWorkspaceId(): string | null {
    return localStorage.getItem(WORKSPACE_ID_KEY);
  },

  setWorkspaceId(workspaceId: string) {
    localStorage.setItem(WORKSPACE_ID_KEY, workspaceId);
  },

  clearWorkspaceId() {
    localStorage.removeItem(WORKSPACE_ID_KEY);
  },

  clearAll() {
    this.clearTokens();
    this.clearWorkspaceId();
  },

  isAuthenticated(): boolean {
    return Boolean(this.getAccessToken() || this.getRefreshToken());
  },
};
