import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppLayout } from "@/components/layout/app-layout";
import { AuthLayout } from "@/components/layout/auth-layout";
import { AIProvidersPage } from "@/pages/ai-providers-page";
import { AcceptInvitePage } from "@/pages/accept-invite-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { BudgetPage } from "@/pages/budget-page";
import { DemoToolkitPage } from "@/pages/demo-toolkit-page";
import { ResourceSharingPage } from "@/pages/resource-sharing-page";
import { BranchManagerPage } from "@/pages/branch-manager-page";
import { BranchOverviewPage } from "@/pages/branch-overview-page";
import { CommitDeepLinkPage } from "@/pages/commit-deep-link-page";
import { CommitGraphPage } from "@/pages/commit-graph-page";
import { ContextPackagePage } from "@/pages/context-package-page";
import { ConversationComparePage } from "@/pages/conversation-compare-page";
import { ConversationHistoryPage } from "@/pages/conversation-history-page";
import { ConversationPage } from "@/pages/conversation-page";
import { ConversationStatsPage } from "@/pages/conversation-stats-page";
import { ConversationTimelinePage } from "@/pages/conversation-timeline-page";
import { HomePage } from "@/pages/home-page";
import { LandingPage } from "@/pages/landing-page";
import { ProjectPage } from "@/pages/project-page";
import { RepositoryPage } from "@/pages/repository-page";
import { LoginPage } from "@/pages/login-page";
import { MembersPage } from "@/pages/members-page";
import { RegisterPage } from "@/pages/register-page";
import { SettingsPage } from "@/pages/settings-page";
import { SystemHealthPage } from "@/pages/system-health-page";

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/app" element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/projects/:projectId" element={<ProjectPage />} />
            <Route path="/repositories/:repositoryId" element={<RepositoryPage />} />
            <Route path="/c/:conversationId" element={<ConversationPage />} />
            <Route path="/c/:conversationId/history" element={<ConversationHistoryPage />} />
            <Route path="/c/:conversationId/overview" element={<BranchOverviewPage />} />
            <Route path="/c/:conversationId/branches" element={<BranchManagerPage />} />
            <Route path="/c/:conversationId/graph" element={<CommitGraphPage />} />
            <Route path="/c/:conversationId/timeline" element={<ConversationTimelinePage />} />
            <Route path="/c/:conversationId/stats" element={<ConversationStatsPage />} />
            <Route path="/c/:conversationId/compare" element={<ConversationComparePage />} />
            <Route path="/commit/:commitHash" element={<CommitDeepLinkPage />} />
            <Route path="/context-packages/:packageId" element={<ContextPackagePage />} />
            <Route path="/members" element={<MembersPage />} />
            <Route path="/invite/:token" element={<AcceptInvitePage />} />
            <Route path="/ai-providers" element={<AIProvidersPage />} />
            <Route path="/budget" element={<BudgetPage />} />
            <Route path="/sharing" element={<ResourceSharingPage />} />
            <Route path="/demo" element={<DemoToolkitPage />} />
            <Route path="/system" element={<SystemHealthPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
