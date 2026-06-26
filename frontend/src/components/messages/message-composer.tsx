import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";

import { messageApi, showApiError } from "@/lib/api";
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
    formState: { errors },
  } = useForm<MessageCreateForm>({
    resolver: zodResolver(messageCreateSchema),
    defaultValues: { content: "" },
  });

  const sendMutation = useMutation({
    mutationFn: (values: MessageCreateForm) =>
      messageApi.create(conversationId, { content: values.content, role: "user" }),
    onSuccess: () => {
      reset();
      void queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
    },
    onError: (error) => showApiError(error, "Unable to send message"),
  });

  const onSubmit = handleSubmit(async (values) => {
    await sendMutation.mutateAsync(values);
  });

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
                void handleSubmit(async (values) => {
                  await sendMutation.mutateAsync(values);
                })();
              }
            }}
          />
          {errors.content && (
            <p className="text-sm text-[var(--color-destructive)]">{errors.content.message}</p>
          )}
        </div>
        <Button type="submit" disabled={sendMutation.isPending} aria-label="Send message">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}
