# Git Integration

## Status

**Partially implemented.**

| Capability | Status |
|------------|--------|
| Repository / branch **metadata** in ConvHub | **Implemented** |
| Coding workspace sync fields | **Implemented** |
| `convhub push` / `convhub pull` (AI context) | **Implemented** |
| Remote Git read/write / automate `git` | **Planned** |

## Intent

Git remains the source of truth for **code**. ConvHub links project memory to repositories so developers can pull code and AI context together — without ConvHub replacing Git.

## Implemented today

- Repository and repository-branch records on projects
- Active developer / sync metadata
- Claude plugin workflow paired with manual `git push` / `git pull`

See [coding-workspaces.md](coding-workspaces.md).

## Still planned

- Deeper Git metadata consumers and automation
- VS Code–assisted Git sync (see [vscode-extension.md](vscode-extension.md))
- Remote Git operations initiated by ConvHub

## Not implemented

ConvHub does **not** currently clone, fetch, push, or rewrite Git remotes.

See [roadmap.md](../../roadmap.md).
