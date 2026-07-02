import { ExternalLink } from "lucide-react";

import { GitHubIcon } from "@/components/landing/github-icon";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SITE_LINKS } from "@/lib/site";

export function OpenSourceSection() {
  return (
    <section id="open-source" className="px-6 py-20 md:py-28">
      <div className="mx-auto max-w-4xl">
        <Card className="overflow-hidden border-[var(--color-border)] bg-gradient-to-br from-[var(--color-card)] to-[var(--color-muted)]/40 shadow-xl">
          <CardHeader className="space-y-4 pb-2 text-center md:px-12 md:pt-12">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--color-muted)]">
              <GitHubIcon className="h-7 w-7" />
            </div>
            <CardTitle className="text-3xl font-semibold md:text-4xl">Open source</CardTitle>
            <CardDescription className="mx-auto max-w-xl text-base leading-relaxed">
              Clone. Run locally. Contribute. Build the future of collaborative AI.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-3 pb-10 md:px-12 md:pb-12 sm:flex-row sm:justify-center">
            <Button asChild size="lg" className="h-11 w-full sm:w-auto">
              <a href={SITE_LINKS.github} target="_blank" rel="noreferrer">
                <GitHubIcon className="mr-2 h-4 w-4" />
                GitHub
              </a>
            </Button>
            <Button asChild variant="outline" size="lg" className="h-11 w-full sm:w-auto">
              <a href={SITE_LINKS.docs} target="_blank" rel="noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                Documentation
              </a>
            </Button>
            <Button asChild variant="outline" size="lg" className="h-11 w-full sm:w-auto">
              <a href={SITE_LINKS.architecture} target="_blank" rel="noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                Architecture
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
