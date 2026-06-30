import { useEffect, useMemo, useState } from "react";

import { useSocket } from "@/context/socket-context";
import { messageResponseSchema, type MessageResponse } from "@/types/api";

export function useConversationRealtime(
  conversationId: string | undefined,
  initialMessages: MessageResponse[],
) {
  const { subscribeConversation, unsubscribeConversation, onEvent } = useSocket();
  const [messages, setMessages] = useState<MessageResponse[]>(initialMessages);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [typingUsers, setTypingUsers] = useState<Record<string, string>>({});

  useEffect(() => {
    setMessages(initialMessages);
  }, [initialMessages]);

  useEffect(() => {
    if (!conversationId) {
      return;
    }
    subscribeConversation(conversationId);
    return () => unsubscribeConversation(conversationId);
  }, [conversationId, subscribeConversation, unsubscribeConversation]);

  useEffect(() => {
    if (!conversationId) {
      return;
    }

    return onEvent((event) => {
      if (event.conversation_id !== conversationId) {
        return;
      }

      if (event.type === "message.created" || event.type === "message.completed") {
        const parsed = messageResponseSchema.safeParse(event.payload);
        if (!parsed.success) {
          return;
        }
        setMessages((current) => {
          const exists = current.some((message) => message.id === parsed.data.id);
          if (exists) {
            return current.map((message) =>
              message.id === parsed.data.id ? parsed.data : message,
            );
          }
          return [...current, parsed.data];
        });
        setStreamingContent(null);
        return;
      }

      if (event.type === "message.streaming") {
        const content = typeof event.payload.content === "string" ? event.payload.content : "";
        setStreamingContent(content);
        return;
      }

      if (event.type === "typing.started") {
        const userId = String(event.payload.user_id ?? "");
        const userName = String(event.payload.user_name ?? "Someone");
        if (!userId) {
          return;
        }
        setTypingUsers((current) => ({ ...current, [userId]: userName }));
        return;
      }

      if (event.type === "typing.stopped") {
        const userId = String(event.payload.user_id ?? "");
        if (!userId) {
          return;
        }
        setTypingUsers((current) => {
          const next = { ...current };
          delete next[userId];
          return next;
        });
      }
    });
  }, [conversationId, onEvent]);

  const typingLabel = useMemo(() => {
    const names = Object.values(typingUsers);
    if (names.length === 0) {
      return null;
    }
    if (names.length === 1) {
      return `${names[0]} is typing...`;
    }
    return `${names.join(", ")} are typing...`;
  }, [typingUsers]);

  return {
    messages,
    streamingContent,
    typingLabel,
    isStreaming: streamingContent !== null,
  };
}
