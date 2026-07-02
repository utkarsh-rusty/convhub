import { NavLink, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, Bot, Coins, FlaskConical, LayoutDashboard, MessageSquare, Settings, Share2, Users } from "lucide-react";

import { demoApi } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { cn } from "@/lib/utils";

const baseNavItems = [
  { to: "/", label: "Conversations", icon: MessageSquare, section: "conversations" as const },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, section: "dashboard" as const },
  { to: "/members", label: "Members", icon: Users, section: "members" as const },
  { to: "/ai-providers", label: "AI Providers", icon: Bot, section: "ai-providers" as const },
  { to: "/system", label: "System", icon: Activity, section: "system" as const, adminOnly: true },
  { to: "/budget", label: "Budget", icon: Coins, section: "budget" as const },
  { to: "/sharing", label: "Resource Sharing", icon: Share2, section: "sharing" as const },
  { to: "/settings", label: "Settings", icon: Settings, section: "settings" as const },
];

const demoNavItem = {
  to: "/demo",
  label: "Demo Toolkit",
  icon: FlaskConical,
  section: "demo" as const,
};

function isActiveSection(pathname: string, section: string) {
  if (section === "conversations") {
    return pathname === "/" || pathname.startsWith("/c/");
  }
  return pathname.startsWith(`/${section}`);
}

export function AppNav() {
  const location = useLocation();
  const { activeWorkspace } = useWorkspace();
  const canViewSystem = ["owner", "admin"].includes(activeWorkspace?.role ?? "");
  const { data: demoConfig } = useQuery({
    queryKey: ["demo-config"],
    queryFn: () => demoApi.getConfig(),
    staleTime: 60_000,
  });

  const navItems = [
    ...baseNavItems.filter((item) => !item.adminOnly || canViewSystem),
    ...(demoConfig?.enabled ? [demoNavItem] : []),
  ];

  return (
    <nav className="space-y-1 px-2 py-3">
      {navItems.map(({ to, label, icon: Icon, section }) => {
        const isActive = isActiveSection(location.pathname, section);
        return (
          <NavLink
            key={to}
            to={to}
            className={() =>
              cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-[var(--color-accent)] text-[var(--color-foreground)]"
                  : "text-[var(--color-muted-foreground)] hover:bg-[var(--color-muted)]/40 hover:text-[var(--color-foreground)]",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        );
      })}
    </nav>
  );
}
