import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { GitHubIcon } from "@/components/landing/github-icon";
import { HeroConversationMock } from "@/components/landing/hero-conversation-mock";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth-context";
import { demoApi } from "@/lib/api";
import { APP_HOME, SITE_LINKS } from "@/lib/site";

export function HeroSection() {
  const { isAuthenticated } = useAuth();
  const { data: demoConfig } = useQuery({
    queryKey: ["demo-config"],
    queryFn: () => demoApi.getConfig(),
    staleTime: 60_000,
  });

  const demoEnabled = Boolean(demoConfig?.enabled);

  return (
    <section className="relative overflow-hidden px-6 pb-20 pt-28 md:pb-28 md:pt-36">
      <div className="landing-hero-gradient pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <p className="mb-4 text-sm font-medium uppercase tracking-[0.2em] text-[var(--color-muted-foreground)]">
            ConvHub
          </p>
          <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl lg:text-6xl">
            GitHub for AI Conversations
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-[var(--color-muted-foreground)]">
            Continue conversations across Claude, ChatGPT, Groq, Gemini, and local models while
            collaborating with your entire team in one shared workspace.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <Button asChild size="lg" className="h-11 px-6 text-base">
              <Link to={isAuthenticated ? APP_HOME : "/login"}>Launch App</Link>
            </Button>
            {demoEnabled ? (
              <Button asChild variant="outline" size="lg" className="h-11 px-6 text-base">
                <Link to="/login">View Demo</Link>
              </Button>
            ) : null}
            <Button asChild variant="outline" size="lg" className="h-11 px-6 text-base">
              <a href={SITE_LINKS.github} target="_blank" rel="noreferrer">
                <GitHubIcon className="mr-2 h-4 w-4" />
                GitHub
              </a>
            </Button>
          </div>
        </div>

        <HeroConversationMock />
      </div>
    </section>
  );
}
