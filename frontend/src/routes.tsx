import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppLayout } from "@/components/layout/app-layout";
import { AuthLayout } from "@/components/layout/auth-layout";
import { AIProvidersPage } from "@/pages/ai-providers-page";
import { AcceptInvitePage } from "@/pages/accept-invite-page";
import { BudgetPage } from "@/pages/budget-page";
import { ResourceSharingPage } from "@/pages/resource-sharing-page";
import { ConversationPage } from "@/pages/conversation-page";
import { HomePage } from "@/pages/home-page";
import { LoginPage } from "@/pages/login-page";
import { MembersPage } from "@/pages/members-page";
import { RegisterPage } from "@/pages/register-page";
import { SettingsPage } from "@/pages/settings-page";

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/c/:conversationId" element={<ConversationPage />} />
            <Route path="/members" element={<MembersPage />} />
            <Route path="/invite/:token" element={<AcceptInvitePage />} />
            <Route path="/ai-providers" element={<AIProvidersPage />} />
            <Route path="/budget" element={<BudgetPage />} />
            <Route path="/sharing" element={<ResourceSharingPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
