import { NavLink, useLocation } from "react-router-dom";
import { Bot, Coins, MessageSquare, Settings, Share2, Users } from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", label: "Conversations", icon: MessageSquare, section: "conversations" as const },
  { to: "/members", label: "Members", icon: Users, section: "members" as const },
  { to: "/ai-providers", label: "AI Providers", icon: Bot, section: "ai-providers" as const },
  { to: "/budget", label: "Budget", icon: Coins, section: "budget" as const },
  { to: "/sharing", label: "Resource Sharing", icon: Share2, section: "sharing" as const },
  { to: "/settings", label: "Settings", icon: Settings, section: "settings" as const },
];

function isActiveSection(pathname: string, section: string) {
  if (section === "conversations") {
    return pathname === "/" || pathname.startsWith("/c/");
  }
  return pathname.startsWith(`/${section}`);
}

export function AppNav() {
  const location = useLocation();

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
