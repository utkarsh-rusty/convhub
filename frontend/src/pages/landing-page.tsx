import { ArchitectureSection } from "@/components/landing/architecture-section";
import { DemoWorkspaceSection } from "@/components/landing/demo-workspace-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { LandingFooter, LandingHeader } from "@/components/landing/landing-chrome";
import { ProvidersSection } from "@/components/landing/providers-section";
import { VisionSection } from "@/components/landing/vision-section";
import { WhyNotGitSection } from "@/components/landing/why-not-git-section";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-foreground)]">
      <LandingHeader />
      <main>
        <HeroSection />
        <FeaturesSection />
        <ArchitectureSection />
        <HowItWorksSection />
        <WhyNotGitSection />
        <ProvidersSection />
        <VisionSection />
        <DemoWorkspaceSection />
      </main>
      <LandingFooter />
    </div>
  );
}
