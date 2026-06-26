import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { authApi } from "@/lib/api";
import { authStorage } from "@/lib/auth-storage";
import type { UserResponse } from "@/types/api";

interface AuthContextValue {
  user: UserResponse | undefined;
  isLoading: boolean;
  isAuthenticated: boolean;
  completeLogin: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [sessionVersion, setSessionVersion] = useState(0);

  const hasSession = useMemo(() => {
    void sessionVersion;
    return authStorage.isAuthenticated();
  }, [sessionVersion]);

  const { data: user, isLoading, isError } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.me,
    enabled: hasSession,
    retry: false,
  });

  const completeLogin = useCallback(() => {
    setSessionVersion((version) => version + 1);
    void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
  }, [queryClient]);

  const logout = useCallback(() => {
    authStorage.clearAll();
    queryClient.clear();
    window.location.href = "/login";
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading: hasSession && isLoading,
      isAuthenticated: hasSession && Boolean(user) && !isError,
      completeLogin,
      logout,
    }),
    [user, isLoading, isError, hasSession, completeLogin, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
