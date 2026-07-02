import { ArchitectureSection } from "@/components/landing/architecture-section";
import { DemoWorkspaceSection } from "@/components/landing/demo-workspace-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { HeroSection } from "@/components/landing/hero-section";
import { LandingFooter, LandingHeader } from "@/components/landing/landing-chrome";
import { OpenSourceSection } from "@/components/landing/open-source-section";
import { ProductShowcase } from "@/components/landing/product-showcase";
import { StoryTimeline } from "@/components/landing/story-timeline";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-foreground)]">
      <LandingHeader />
      <main>
        <HeroSection />
        <StoryTimeline />
        <FeaturesSection />
        <ArchitectureSection />
        <ProductShowcase />
        <DemoWorkspaceSection />
        <OpenSourceSection />
      </main>
      <LandingFooter />
    </div>
  );
}
