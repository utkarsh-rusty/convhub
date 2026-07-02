import type { ExecutionSummary, RoutingPolicyType } from "@/types/api";

const ROUTING_POLICY_LABELS: Record<RoutingPolicyType, string> = {
  owner_first: "Owner First",
  balanced: "Balanced",
  lowest_usage: "Lowest Usage",
  cheapest: "Cheapest",
  priority: "Priority",
};

const MODEL_LABELS: Record<string, string> = {
  "claude-sonnet-4-20250514": "Claude Sonnet 4",
  "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
  "gpt-4o": "GPT-4o",
  "gpt-4o-mini": "GPT-4o Mini",
  "gemini-2.0-flash": "Gemini 2.0 Flash",
  "gemini-1.5-pro": "Gemini 1.5 Pro",
  "llama-3.3-70b-versatile": "Llama 3.3 70B",
  "llama-3.1-8b-instant": "Llama 3.1 8B Instant",
  "llama3.2": "Llama 3.2",
  mock: "Mock",
};

export function formatModelLabel(model: string, provider?: string) {
  if (MODEL_LABELS[model]) {
    return MODEL_LABELS[model];
  }
  if (provider === "ollama") {
    return model.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }
  if (provider === "anthropic" && model.includes("sonnet")) {
    return "Claude Sonnet";
  }
  if (provider === "openai" && model.startsWith("gpt")) {
    return model.toUpperCase().replace(/-/g, " ");
  }
  if (provider === "gemini") {
    return model.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }
  if (provider === "groq") {
    return model.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }
  return model;
}

export function formatRoutingPolicy(policy: RoutingPolicyType) {
  return ROUTING_POLICY_LABELS[policy] ?? policy;
}

export function formatExecutionBadge(execution: ExecutionSummary) {
  const modelLabel = formatModelLabel(execution.model, execution.provider);
  const providerLabel =
    execution.provider.charAt(0).toUpperCase() + execution.provider.slice(1);

  switch (execution.execution_type) {
    case "borrowed_provider":
      return `Borrowed from ${execution.borrowed_from ?? execution.owner_name ?? "teammate"} · ${providerLabel}`;
    case "local_model":
      return `${modelLabel} · Local Model`;
    default:
      return `${execution.owner_name ?? "You"} · ${providerLabel}`;
  }
}

export function formatExecutionHeader(execution: ExecutionSummary) {
  const providerLabel =
    execution.provider.charAt(0).toUpperCase() + execution.provider.slice(1);

  if (execution.execution_type === "borrowed_provider") {
    const lender = execution.borrowed_from ?? execution.owner_name ?? "teammate";
    return `Borrowed from ${lender} · ${providerLabel}`;
  }
  if (execution.execution_type === "local_model") {
    return `Local · ${formatModelLabel(execution.model, execution.provider)}`;
  }
  return `${execution.owner_name ?? "You"} · ${providerLabel}`;
}

export function formatCredits(value: string | number) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatTimestamp(value: string) {
  const date = new Date(value);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (isToday) {
    return `Today ${time}`;
  }

  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function providerStatusLabel(isActive: boolean, requestCount: number) {
  if (!isActive) {
    return "Inactive";
  }
  if (requestCount > 0) {
    return "Healthy";
  }
  return "Ready";
}
