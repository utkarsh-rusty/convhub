import { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { chatApi, messageApi, showApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSocket } from "@/context/socket-context";
import { useWorkspace } from "@/context/workspace-context";
import { messageCreateSchema, type MessageCreateForm } from "@/types/api";
import { Button } from "@/components/ui/button";

interface MessageComposerProps {
  conversationId: string;
  onGeneratingChange?: (isGenerating: boolean) => void;
}

export function MessageComposer({ conversationId, onGeneratingChange }: MessageComposerProps) {
  const queryClient = useQueryClient();
  const { activeWorkspaceId } = useWorkspace();
  const { sendTyping } = useSocket();
  const typingTimeoutRef = useRef<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    getValues,
    watch,
    formState: { errors },
  } = useForm<MessageCreateForm>({
    resolver: zodResolver(messageCreateSchema),
    defaultValues: { content: "" },
  });

  const contentValue = watch("content");
  const { ref: contentRef, ...contentRegister } = register("content");

  const resizeTextarea = (element: HTMLTextAreaElement | null) => {
    if (!element) {
      return;
    }
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
  };

  useEffect(() => {
    resizeTextarea(textareaRef.current);
  }, [contentValue]);

  const invalidateMessages = () => {
    void queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
    void queryClient.invalidateQueries({ queryKey: ["conversations", activeWorkspaceId] });
  };

  const stopTyping = () => {
    if (typingTimeoutRef.current !== null) {
      window.clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    sendTyping(conversationId, false);
  };

  const handleTyping = () => {
    sendTyping(conversationId, true);
    if (typingTimeoutRef.current !== null) {
      window.clearTimeout(typingTimeoutRef.current);
    }
    typingTimeoutRef.current = window.setTimeout(() => {
      sendTyping(conversationId, false);
      typingTimeoutRef.current = null;
    }, 3000);
  };

  useEffect(() => () => stopTyping(), [conversationId]);

  const sendMutation = useMutation({
    mutationFn: (values: MessageCreateForm) =>
      messageApi.create(conversationId, { content: values.content, role: "user" }),
    onSuccess: () => {
      stopTyping();
      reset();
      invalidateMessages();
    },
    onError: (error) => showApiError(error, "Unable to send message"),
  });

  const askAiMutation = useMutation({
    mutationFn: (content: string) =>
      chatApi.send({ conversation_id: conversationId, content }),
    onMutate: () => {
      stopTyping();
      onGeneratingChange?.(true);
    },
    onSuccess: () => {
      reset();
      invalidateMessages();
      toast.success("AI response received");
    },
    onError: (error) => showApiError(error, "Unable to get AI response"),
    onSettled: () => {
      onGeneratingChange?.(false);
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    await sendMutation.mutateAsync(values);
  });

  const onAskAi = handleSubmit(async (values) => {
    await askAiMutation.mutateAsync(values.content);
  });

  const isPending = sendMutation.isPending || askAiMutation.isPending;

  return (
    <div className="shrink-0 border-t border-[var(--color-border)] bg-[var(--color-card)] px-4 py-2.5 sm:px-5">
      <form onSubmit={onSubmit} className="relative">
        <div className="flex items-end gap-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-background)] px-2 py-1.5 shadow-sm focus-within:ring-1 focus-within:ring-[var(--color-ring)]">
          <textarea
            placeholder="Write a message..."
            rows={1}
            className="max-h-40 min-h-[36px] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-5 outline-none placeholder:text-[var(--color-muted-foreground)]"
            {...contentRegister}
            ref={(element) => {
              contentRef(element);
              textareaRef.current = element;
            }}
            onChange={(event) => {
              void contentRegister.onChange(event);
              resizeTextarea(event.currentTarget);
              if (event.target.value.trim()) {
                handleTyping();
              } else {
                stopTyping();
              }
            }}
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
          <div className="flex shrink-0 items-center gap-0.5 pb-0.5">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              disabled={isPending}
              onClick={() => void onAskAi()}
              aria-label="Ask AI"
              title="Ask AI"
            >
              <Sparkles className={cn("h-4 w-4", askAiMutation.isPending && "animate-spin")} />
            </Button>
            <Button
              type="submit"
              size="icon"
              className="h-8 w-8"
              disabled={isPending}
              aria-label="Send message"
              title="Send"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {errors.content ? (
          <p className="mt-1 text-xs text-[var(--color-destructive)]">{errors.content.message}</p>
        ) : null}
      </form>
    </div>
  );
}
