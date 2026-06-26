import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, TestTube } from "lucide-react";
import { toast } from "sonner";

import { aiAccountApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { aiAccountCreateSchema, type AIAccountCreateForm, type AIProviderName } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

export function AIProvidersPage() {
  const queryClient = useQueryClient();
  const { activeWorkspace, activeWorkspaceId } = useWorkspace();
  const [open, setOpen] = useState(false);
  const canManage = ["owner", "admin"].includes(activeWorkspace?.role ?? "");

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["ai-accounts", activeWorkspaceId],
    queryFn: aiAccountApi.list,
    enabled: Boolean(activeWorkspaceId && canManage),
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AIAccountCreateForm>({
    resolver: zodResolver(aiAccountCreateSchema),
    defaultValues: { provider: "mock", is_active: true, priority: 0 },
  });

  const selectedProvider = watch("provider");

  const createMutation = useMutation({
    mutationFn: aiAccountApi.create,
    onSuccess: () => {
      toast.success("AI provider account created");
      reset();
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["ai-accounts", activeWorkspaceId] });
    },
    onError: (error) => showApiError(error, "Unable to create AI account"),
  });

  const testMutation = useMutation({
    mutationFn: aiAccountApi.test,
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    },
    onError: (error) => showApiError(error, "Unable to test AI account"),
  });

  const deleteMutation = useMutation({
    mutationFn: aiAccountApi.remove,
    onSuccess: () => {
      toast.success("AI provider removed");
      void queryClient.invalidateQueries({ queryKey: ["ai-accounts", activeWorkspaceId] });
    },
    onError: (error) => showApiError(error, "Unable to remove AI account"),
  });

  if (!activeWorkspaceId) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Select a workspace to manage AI providers.
      </div>
    );
  }

  if (!canManage) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-sm text-[var(--color-muted-foreground)]">
        Only workspace owners and admins can manage AI providers.
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">AI Providers</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Workspace credentials for the AI gateway
          </p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add provider
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add AI provider</DialogTitle>
              <DialogDescription>
                {selectedProvider === "ollama"
                  ? "Ollama uses your local server; no API key is required."
                  : "API keys are encrypted and never shown again after saving."}
              </DialogDescription>
            </DialogHeader>
            <form
              onSubmit={handleSubmit(async (values) => {
                const payload = {
                  ...values,
                  api_key: values.provider === "ollama" ? undefined : values.api_key,
                };
                await createMutation.mutateAsync(payload);
              })}
              className="space-y-4"
            >
              <div className="space-y-2">
                <Label>Provider</Label>
                <Select
                  value={selectedProvider}
                  onValueChange={(value: AIProviderName) => setValue("provider", value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="mock">Mock</SelectItem>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                    <SelectItem value="ollama">Ollama</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="display_name">Display name</Label>
                <Input id="display_name" {...register("display_name")} />
                {errors.display_name && (
                  <p className="text-sm text-[var(--color-destructive)]">
                    {errors.display_name.message}
                  </p>
                )}
              </div>
              {selectedProvider !== "ollama" && (
                <div className="space-y-2">
                  <Label htmlFor="api_key">API key</Label>
                  <Input id="api_key" type="password" {...register("api_key")} />
                  {errors.api_key && (
                    <p className="text-sm text-[var(--color-destructive)]">{errors.api_key.message}</p>
                  )}
                </div>
              )}
              <Button type="submit" className="w-full" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Saving..." : "Save provider"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={index} className="h-20 w-full" />
            ))}
          </div>
        ) : accounts.length === 0 ? (
          <p className="text-sm text-[var(--color-muted-foreground)]">
            No AI providers configured yet.
          </p>
        ) : (
          <div className="space-y-3">
            {accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-4 py-4"
              >
                <div>
                  <p className="font-medium">{account.display_name}</p>
                  <p className="text-sm text-[var(--color-muted-foreground)]">
                    {account.provider} · priority {account.priority} ·{" "}
                    {account.is_active ? "active" : "inactive"}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={testMutation.isPending}
                    onClick={() => testMutation.mutate(account.id)}
                  >
                    <TestTube className="mr-2 h-4 w-4" />
                    Test
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(account.id)}
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
