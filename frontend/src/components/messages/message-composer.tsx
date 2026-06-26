import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { chatApi, messageApi, showApiError } from "@/lib/api";
import { useWorkspace } from "@/context/workspace-context";
import { messageCreateSchema, type MessageCreateForm } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface MessageComposerProps {
  conversationId: string;
}

export function MessageComposer({ conversationId }: MessageComposerProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();

  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors },
  } = useForm<MessageCreateForm>({
    resolver: zodResolver(messageCreateSchema),
    defaultValues: { content: "" },
  });

  const invalidateMessages = () => {
    void queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
    void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
  };

  const sendMutation = useMutation({
    mutationFn: (values: MessageCreateForm) =>
      messageApi.create(conversationId, { content: values.content, role: "user" }),
    onSuccess: () => {
      reset();
      invalidateMessages();
    },
    onError: (error) => showApiError(error, "Unable to send message"),
  });

  const askAiMutation = useMutation({
    mutationFn: (content: string) =>
      chatApi.send({ conversation_id: conversationId, content }),
    onSuccess: () => {
      reset();
      invalidateMessages();
      toast.success("AI response received");
    },
    onError: (error) => showApiError(error, "Unable to get AI response"),
  });

  const onSubmit = handleSubmit(async (values) => {
    await sendMutation.mutateAsync(values);
  });

  const onAskAi = handleSubmit(async (values) => {
    await askAiMutation.mutateAsync(values.content);
  });

  const isPending = sendMutation.isPending || askAiMutation.isPending;

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-card)] px-6 py-4">
      <form onSubmit={onSubmit} className="flex items-end gap-3">
        <div className="flex-1 space-y-2">
          <Textarea
            placeholder="Write a message..."
            rows={3}
            {...register("content")}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                const content = getValues("content");
                if (content.trim()) {
                  void sendMutation.mutateAsync({ content });
                }
              }
            }}
          />
          {errors.content && (
            <p className="text-sm text-[var(--color-destructive)]">{errors.content.message}</p>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={isPending}
            onClick={() => void onAskAi()}
          >
            <Sparkles className="mr-2 h-4 w-4" />
            Ask AI
          </Button>
          <Button type="submit" disabled={isPending} aria-label="Send message">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}
