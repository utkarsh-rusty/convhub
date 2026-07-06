import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  FolderKanban,
  GitBranch,
  Lock,
  MessageSquarePlus,
  Pencil,
  Plus,
  RotateCcw,
} from "lucide-react";
import { NavLink, useParams } from "react-router-dom";

import { conversationApi, projectApi } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import { useAuth } from "@/context/auth-context";
import { useWorkspace } from "@/context/workspace-context";
import { CreateConversationDialog } from "@/components/conversation/create-conversation-dialog";
import { RenameConversationDialog } from "@/components/conversation/rename-conversation-dialog";
import { CreateProjectDialog } from "@/components/project/create-project-dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ConversationResponse, ProjectResponse } from "@/types/api";

function collapseStorageKey(workspaceId: string) {
  return `convhub.project-collapse.${workspaceId}`;
}

function selectedProjectStorageKey(workspaceId: string) {
  return `convhub.selected-project.${workspaceId}`;
}

function loadCollapsedMap(workspaceId: string): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(collapseStorageKey(workspaceId));
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function saveCollapsedMap(workspaceId: string, map: Record<string, boolean>) {
  localStorage.setItem(collapseStorageKey(workspaceId), JSON.stringify(map));
}

export function ConversationSidebar() {
  const { conversationId, projectId: routeProjectId } = useParams();
  const { activeWorkspaceId } = useWorkspace();
  const [createConversationOpen, setCreateConversationOpen] = useState(false);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>();
  const [collapsedMap, setCollapsedMap] = useState<Record<string, boolean>>({});

  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ["projects", activeWorkspaceId],
    queryFn: () => projectApi.list(),
    enabled: Boolean(activeWorkspaceId),
    refetchOnWindowFocus: true,
  });

  const { data: conversations = [], isLoading: conversationsLoading, isError } = useQuery({
    queryKey: ["conversations", activeWorkspaceId],
    queryFn: conversationApi.list,
    enabled: Boolean(activeWorkspaceId),
    refetchOnWindowFocus: true,
  });

  useEffect(() => {
    if (!activeWorkspaceId) {
      return;
    }
    setCollapsedMap(loadCollapsedMap(activeWorkspaceId));
    const stored = localStorage.getItem(selectedProjectStorageKey(activeWorkspaceId));
    setSelectedProjectId(stored ?? undefined);
  }, [activeWorkspaceId]);

  useEffect(() => {
    if (routeProjectId) {
      setSelectedProjectId(routeProjectId);
      if (activeWorkspaceId) {
        localStorage.setItem(selectedProjectStorageKey(activeWorkspaceId), routeProjectId);
      }
    }
  }, [routeProjectId, activeWorkspaceId]);

  useEffect(() => {
    if (!conversationId || !conversations.length || !activeWorkspaceId) {
      return;
    }
    const active = conversations.find((item) => item.id === conversationId);
    if (!active) {
      return;
    }
    setSelectedProjectId(active.project_id);
    localStorage.setItem(selectedProjectStorageKey(activeWorkspaceId), active.project_id);
    setCollapsedMap((current) => {
      if (current[active.project_id] === false) {
        return current;
      }
      const next = { ...current, [active.project_id]: false };
      saveCollapsedMap(activeWorkspaceId, next);
      return next;
    });
  }, [conversationId, conversations, activeWorkspaceId]);

  const conversationsByProject = useMemo(() => {
    const map = new Map<string, ConversationResponse[]>();
    for (const conversation of conversations) {
      const list = map.get(conversation.project_id) ?? [];
      list.push(conversation);
      map.set(conversation.project_id, list);
    }
    return map;
  }, [conversations]);

  const toggleProject = (projectId: string) => {
    if (!activeWorkspaceId) {
      return;
    }
    setCollapsedMap((current) => {
      const next = { ...current, [projectId]: !(current[projectId] ?? false) };
      saveCollapsedMap(activeWorkspaceId, next);
      return next;
    });
  };

  const isLoading = projectsLoading || conversationsLoading;
  const defaultProjectId =
    selectedProjectId ||
    projects.find((project) => project.is_default)?.id ||
    projects[0]?.id;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between px-3 py-2.5">
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--color-muted-foreground)]">
          Projects
        </p>
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="New project"
            disabled={!activeWorkspaceId}
            onClick={() => setCreateProjectOpen(true)}
          >
            <Plus className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="New conversation"
            disabled={!activeWorkspaceId}
            onClick={() => setCreateConversationOpen(true)}
          >
            <MessageSquarePlus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1 px-1.5 pb-3">
        {isLoading ? (
          <div className="space-y-2 px-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : isError ? (
          <div className="px-3 py-6 text-xs text-[var(--color-muted-foreground)]">
            Could not load projects.
          </div>
        ) : projects.length === 0 ? (
          <div className="px-3 py-6 text-xs text-[var(--color-muted-foreground)]">
            No projects yet.
          </div>
        ) : (
          <div className="space-y-2">
            {projects.map((project) => {
              const projectConversations = conversationsByProject.get(project.id) ?? [];
              const collapsed = collapsedMap[project.id] ?? false;
              const tree = buildConversationTree(projectConversations);
              return (
                <ProjectSection
                  key={project.id}
                  project={project}
                  collapsed={collapsed}
                  activeConversationId={conversationId}
                  tree={tree}
                  onToggle={() => toggleProject(project.id)}
                  onSelect={() => {
                    setSelectedProjectId(project.id);
                    if (activeWorkspaceId) {
                      localStorage.setItem(
                        selectedProjectStorageKey(activeWorkspaceId),
                        project.id,
                      );
                    }
                  }}
                />
              );
            })}
          </div>
        )}
      </ScrollArea>

      <CreateConversationDialog
        open={createConversationOpen}
        onOpenChange={setCreateConversationOpen}
        defaultProjectId={defaultProjectId}
      />
      <CreateProjectDialog open={createProjectOpen} onOpenChange={setCreateProjectOpen} />
    </div>
  );
}

function ProjectSection({
  project,
  collapsed,
  activeConversationId,
  tree,
  onToggle,
  onSelect,
}: {
  project: ProjectResponse;
  collapsed: boolean;
  activeConversationId?: string;
  tree: ConversationTreeNode[];
  onToggle: () => void;
  onSelect: () => void;
}) {
  const accent = project.color || "var(--color-muted-foreground)";

  return (
    <div className="rounded-md border border-transparent">
      <div className="flex items-center gap-0.5">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0"
          aria-label={collapsed ? "Expand project" : "Collapse project"}
          onClick={onToggle}
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </Button>
        <NavLink
          to={`/projects/${project.id}`}
          onClick={onSelect}
          className={({ isActive }) =>
            cn(
              "flex min-w-0 flex-1 items-center gap-1.5 rounded-md px-1.5 py-1 text-sm hover:bg-[var(--color-accent)]",
              isActive && "bg-[var(--color-accent)]",
            )
          }
        >
          <span
            className="mt-0.5 inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm"
            style={{ backgroundColor: accent }}
            aria-hidden="true"
          >
            <FolderKanban className="h-2.5 w-2.5 text-white" />
          </span>
          <span className="truncate text-[13px] font-semibold">{project.name}</span>
          <span className="ml-auto shrink-0 text-[10px] text-[var(--color-muted-foreground)]">
            {project.conversation_count}
          </span>
        </NavLink>
      </div>

      {!collapsed ? (
        <div className="ml-3 space-y-0.5 border-l border-[var(--color-border)] pl-1.5">
          {tree.length === 0 ? (
            <p className="px-2 py-1 text-[11px] text-[var(--color-muted-foreground)]">
              No conversations
            </p>
          ) : (
            tree.map((node) => (
              <ConversationTreeNodeView
                key={node.conversation.id}
                node={node}
                activeId={activeConversationId}
              />
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

interface ConversationTreeNode {
  conversation: ConversationResponse;
  children: ConversationTreeNode[];
}

export function buildConversationTree(
  conversations: ConversationResponse[],
): ConversationTreeNode[] {
  const byId = new Map(
    conversations.map((conversation) => [
      conversation.id,
      { conversation, children: [] as ConversationTreeNode[] },
    ]),
  );
  const roots: ConversationTreeNode[] = [];

  for (const conversation of conversations) {
    const node = byId.get(conversation.id)!;
    const parentId = conversation.parent_conversation_id ?? null;
    if (parentId && byId.has(parentId)) {
      byId.get(parentId)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function ConversationTreeNodeView({
  node,
  activeId,
  depth = 0,
}: {
  node: ConversationTreeNode;
  activeId?: string;
  depth?: number;
}) {
  const hasChildren = node.children.length > 0;
  const containsActive =
    node.conversation.id === activeId ||
    node.children.some((child) => containsConversation(child, activeId));
  const [expanded, setExpanded] = useState(containsActive || depth === 0);

  return (
    <div>
      <div className="flex items-start gap-0.5">
        {hasChildren ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="mt-0.5 h-6 w-6 shrink-0 transition-colors duration-150"
            aria-label={expanded ? "Collapse branch" : "Expand branch"}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? (
              <ChevronDown className="h-3 w-3 transition-transform duration-150" />
            ) : (
              <ChevronRight className="h-3 w-3 transition-transform duration-150" />
            )}
          </Button>
        ) : (
          <span className="inline-block h-6 w-6 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <ConversationSidebarItem
            conversation={node.conversation}
            active={node.conversation.id === activeId}
            isBranch={depth > 0}
          />
        </div>
      </div>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200 ease-out",
          hasChildren && expanded ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0",
        )}
      >
        {hasChildren ? (
          <div className="ml-3 space-y-0.5 border-l border-[var(--color-border)] pl-1">
            {node.children.map((child) => (
              <ConversationTreeNodeView
                key={child.conversation.id}
                node={child}
                activeId={activeId}
                depth={depth + 1}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function containsConversation(node: ConversationTreeNode, activeId?: string): boolean {
  if (!activeId) {
    return false;
  }
  if (node.conversation.id === activeId) {
    return true;
  }
  return node.children.some((child) => containsConversation(child, activeId));
}

function ConversationSidebarItem({
  conversation,
  active,
  isBranch = false,
}: {
  conversation: ConversationResponse;
  active: boolean;
  isBranch?: boolean;
}) {
  const { user } = useAuth();
  const [renameOpen, setRenameOpen] = useState(false);
  const branchLabel = conversation.branch_name?.trim();
  const isOwner = conversation.owner_id === user?.id;
  const isReadOnly = !conversation.is_participant;
  const commitCount = conversation.commit_count ?? 0;
  const activity = conversation.latest_activity_at ?? conversation.last_activity_at;

  return (
    <>
      <div
        className={cn(
          "group flex items-start gap-1 rounded-md px-1.5 py-1 transition-colors duration-150",
          active && "bg-[var(--color-accent)]",
          conversation.is_restored && "border-l-2 border-sky-500/60 pl-1",
        )}
      >
        <NavLink
          to={`/c/${conversation.id}`}
          className="flex min-w-0 flex-1 items-start gap-1.5 text-sm hover:text-[var(--color-foreground)]"
        >
          <span className="mt-0.5 text-[var(--color-muted-foreground)]" aria-hidden="true">
            {conversation.is_restored ? (
              <RotateCcw className="h-3 w-3 text-sky-600 dark:text-sky-400" />
            ) : isBranch ? (
              <GitBranch className="h-3 w-3" />
            ) : (
              <span className="inline-block h-3 w-3 text-center text-[10px]">●</span>
            )}
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="block truncate text-[13px] font-medium leading-tight">
                {branchLabel || conversation.title}
              </span>
              {conversation.is_restored ? (
                <span className="shrink-0 rounded-full bg-sky-500/10 px-1 py-px text-[9px] font-medium uppercase tracking-wide text-sky-700 dark:text-sky-300">
                  Restored
                </span>
              ) : null}
            </span>
            <span className="mt-0.5 flex items-center gap-1.5 text-[10px] leading-tight text-[var(--color-muted-foreground)]">
              <span>
                {commitCount} commit{commitCount === 1 ? "" : "s"}
              </span>
              <span aria-hidden="true">·</span>
              <span className="truncate">{formatTimestamp(activity)}</span>
              {isReadOnly ? (
                <Lock className="h-2.5 w-2.5 shrink-0" aria-label="Read-only" />
              ) : null}
            </span>
          </span>
        </NavLink>
        {isOwner ? (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 transition-opacity duration-150 group-hover:opacity-100"
            aria-label="Rename conversation"
            onClick={() => setRenameOpen(true)}
          >
            <Pencil className="h-3 w-3" />
          </Button>
        ) : null}
      </div>

      {isOwner ? (
        <RenameConversationDialog
          conversation={conversation}
          open={renameOpen}
          onOpenChange={setRenameOpen}
        />
      ) : null}
    </>
  );
}
