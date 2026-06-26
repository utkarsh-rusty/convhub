import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import { AuthProvider } from "@/context/auth-context";
import { WorkspaceProvider } from "@/context/workspace-context";
import { queryClient } from "@/lib/query-client";
import { AppRoutes } from "@/routes";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WorkspaceProvider>
          <AppRoutes />
          <Toaster theme="dark" richColors position="top-right" />
        </WorkspaceProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
