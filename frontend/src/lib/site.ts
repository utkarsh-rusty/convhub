export const GITHUB_REPO = "https://github.com/utkarsh-rusty/convhub";

export const SITE_LINKS = {
  github: GITHUB_REPO,
  docs: `${GITHUB_REPO}/blob/main/docs/index.md`,
  architecture: `${GITHUB_REPO}/tree/main/docs/architecture`,
  contributing: `${GITHUB_REPO}/blob/main/CONTRIBUTING.md`,
  license: `${GITHUB_REPO}/blob/main/LICENSE`,
  roadmap: `${GITHUB_REPO}/blob/main/roadmap.md`,
} as const;

export const APP_VERSION = "0.1.0";

/** Protected app entry (conversations home redirect). */
export const APP_HOME = "/app";
