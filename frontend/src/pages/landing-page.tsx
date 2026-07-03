import { ArchitectureSection } from "@/components/landing/architecture-section";
import { DemoWorkspaceSection } from "@/components/landing/demo-workspace-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HeroSection } from "@/components/landing/hero-section";
import { LandingFooter, LandingHeader } from "@/components/landing/landing-chrome";
import { OneConversationSection } from "@/components/landing/one-conversation-section";
import { OwnershipFirstSection } from "@/components/landing/ownership-first-section";
import { RoadmapSection } from "@/components/landing/roadmap-section";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-foreground)]">
      <LandingHeader />
      <main>
        <HeroSection />
        <OneConversationSection />
        <OwnershipFirstSection />
        <FeaturesSection />
        <ArchitectureSection />
        <RoadmapSection />
        <DemoWorkspaceSection />
      </main>
      <LandingFooter />
    </div>
  );
}
