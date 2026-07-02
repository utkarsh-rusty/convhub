import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import { AuthProvider } from "@/context/auth-context";
import { SocketProvider } from "@/context/socket-context";
import { WorkspaceProvider } from "@/context/workspace-context";
import { queryClient } from "@/lib/query-client";
import { AppRoutes } from "@/routes";
import "./index.css";

const storedTheme = localStorage.getItem("convhub-theme");
const systemTheme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
document.documentElement.dataset.theme =
  storedTheme === "light" || storedTheme === "dark" ? storedTheme : systemTheme;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WorkspaceProvider>
          <SocketProvider>
            <AppRoutes />
            <Toaster theme="dark" richColors position="top-right" />
          </SocketProvider>
        </WorkspaceProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
