import { Outlet } from "react-router-dom";
import { LogOut } from "lucide-react";

import { WorkspaceSelector } from "@/components/workspace/workspace-selector";
import { CreateWorkspaceDialog } from "@/components/workspace/create-workspace-dialog";
import { ConversationSidebar } from "@/components/conversation/conversation-sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/context/auth-context";

export function AppLayout() {
  const { user, logout } = useAuth();
  const initials = user?.name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex h-screen bg-[var(--color-background)] text-[var(--color-foreground)]">
      <aside className="flex w-72 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-card)]">
        <div className="flex items-center justify-between px-4 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-muted-foreground)]">
              ConvHub
            </p>
            <h1 className="text-lg font-semibold">Workspace</h1>
          </div>
          <CreateWorkspaceDialog />
        </div>

        <div className="px-4 pb-4">
          <WorkspaceSelector />
        </div>

        <Separator />

        <ConversationSidebar />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-[var(--color-border)] px-6">
          <div className="text-sm text-[var(--color-muted-foreground)]">
            Shared AI workspace for your team
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-[var(--color-muted-foreground)]">{user?.email}</p>
            </div>
            <Avatar>
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>

        <main className="flex min-h-0 flex-1 flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
