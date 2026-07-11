import { Link } from "react-router-dom";
import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth-context";
import { useTheme } from "@/hooks/use-theme";
import { APP_HOME, APP_VERSION, SITE_LINKS } from "@/lib/site";

const NAV_LINKS: Array<
  { href: string; label: string; external?: boolean }
> = [
  { href: "#features", label: "Features" },
  { href: "#architecture", label: "Architecture" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#vision", label: "Vision" },
  { href: SITE_LINKS.docs, label: "Docs", external: true },
];

export function LandingHeader() {
  const { isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="fixed inset-x-0 top-0 z-40 border-b border-[var(--color-border)]/60 bg-[var(--color-background)]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link to="/" className="text-lg font-semibold tracking-tight" aria-label="ConvHub home">
          ConvHub
        </Link>

        <nav className="hidden items-center gap-6 md:flex" aria-label="Primary">
          {NAV_LINKS.map((link) =>
            link.external ? (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-[var(--color-muted-foreground)] transition-colors hover:text-[var(--color-foreground)]"
              >
                {link.label}
              </a>
            ) : (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-[var(--color-muted-foreground)] transition-colors hover:text-[var(--color-foreground)]"
              >
                {link.label}
              </a>
            ),
          )}
        </nav>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-md border border-[var(--color-border)] transition-colors hover:bg-[var(--color-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-ring)]"
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          {!isAuthenticated ? (
            <Button asChild variant="ghost" size="sm">
              <Link to="/login">Log in</Link>
            </Button>
          ) : null}
          <Button asChild size="sm">
            <Link to={isAuthenticated ? APP_HOME : "/login"}>
              {isAuthenticated ? "Open App" : "Launch App"}
            </Link>
          </Button>
        </div>
      </div>
    </header>
  );
}

export function LandingFooter() {
  const footerLinks = [
    { href: SITE_LINKS.docs, label: "Documentation" },
    { href: SITE_LINKS.github, label: "GitHub" },
    { href: SITE_LINKS.architecture, label: "Architecture" },
    { href: SITE_LINKS.contributing, label: "Contributing" },
    { href: SITE_LINKS.license, label: "License" },
    { href: SITE_LINKS.roadmap, label: "Roadmap" },
  ] as const;

  return (
    <footer className="border-t border-[var(--color-border)] px-6 py-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-lg font-semibold">ConvHub</p>
          <p className="mt-1 max-w-sm text-sm text-[var(--color-muted-foreground)]">
            Built in public. MIT licensed. Contributions welcome.
          </p>
          <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">
            Continue your teammate&apos;s AI coding session.
          </p>
          <p className="mt-3 text-xs text-[var(--color-muted-foreground)]">v{APP_VERSION}</p>
        </div>

        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-6 gap-y-2">
            {footerLinks.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-[var(--color-muted-foreground)] transition-colors hover:text-[var(--color-foreground)]"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
