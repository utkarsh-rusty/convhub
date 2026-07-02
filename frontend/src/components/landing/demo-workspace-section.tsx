import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRightLeft, GitBranch, MessageSquare, Radio, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { demoApi } from "@/lib/api";

const DEMO_USERS = [
  {
    name: "Alice",
    role: "Owner",
    initials: "A",
    highlights: ["Shared conversations", "Routing", "Live collaboration"],
  },
  {
    name: "Bob",
    role: "Admin",
    initials: "B",
    highlights: ["Multiple providers", "Budget governance", "Borrowing"],
  },
  {
    name: "Charlie",
    role: "Member",
    initials: "C",
    highlights: ["Shared conversations", "Borrowing", "Real-time presence"],
  },
] as const;

const HIGHLIGHT_ICONS = {
  "Shared conversations": MessageSquare,
  Routing: GitBranch,
  "Live collaboration": Radio,
  "Multiple providers": Sparkles,
  "Budget governance": GitBranch,
  Borrowing: ArrowRightLeft,
  "Real-time presence": Radio,
} as const;

export function DemoWorkspaceSection() {
  const { data: demoConfig } = useQuery({
    queryKey: ["demo-config"],
    queryFn: () => demoApi.getConfig(),
    staleTime: 60_000,
  });

  if (!demoConfig?.enabled) {
    return null;
  }

  return (
    <section id="demo" className="border-y border-[var(--color-border)] bg-[var(--color-muted)]/20 px-6 py-20 md:py-28">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Demo workspace</h2>
        <p className="mt-4 max-w-2xl text-[var(--color-muted-foreground)]">
          Jump in as Alice, Bob, or Charlie and explore a seeded team workspace in seconds.
        </p>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {DEMO_USERS.map((user) => (
            <Card key={user.name} className="transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Avatar className="h-12 w-12">
                    <AvatarFallback>{user.initials}</AvatarFallback>
                  </Avatar>
                  <div>
                    <CardTitle>{user.name}</CardTitle>
                    <CardDescription>{user.role}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-[var(--color-muted-foreground)]">
                  {user.highlights.map((item) => {
                    const Icon = HIGHLIGHT_ICONS[item];
                    return (
                      <li key={item} className="flex items-center gap-2">
                        <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                        {item}
                      </li>
                    );
                  })}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-10 flex justify-center">
          <Button asChild size="lg" className="h-11 px-6">
            <Link to="/login">Launch Demo Workspace</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
