from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.ai.providers.base import ChatMessage
from app.models.conversation import Conversation
from app.models.conversation_participant import ConversationParticipant
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.workspace import Workspace

_METADATA_SEPARATOR = "------------------------------------"


@dataclass(frozen=True)
class PromptContext:
    """Provider-ready prompt package produced solely by PromptBuilder."""

    system_prompt: str
    chat_messages: list[ChatMessage]
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptBuilder:
    """Single place that converts collaboration context into provider-ready prompts."""

    def build(
        self,
        *,
        workspace: Workspace,
        conversation: Conversation,
        participants: list[ConversationParticipant],
        messages: list[Message],
        base_system_prompt: str,
        author_names: dict[UUID, str],
    ) -> PromptContext:
        participant_names = self._participant_names(participants)
        system_prompt = self._compose_system_prompt(
            workspace_name=workspace.name,
            conversation_title=conversation.title,
            participant_names=participant_names,
            base_system_prompt=base_system_prompt,
            # TODO: append conversation snapshot section when snapshot service exists.
            # TODO: append retrieved documents section when RAG retrieval is added.
            # TODO: append code context section when repository context is wired in.
            # TODO: append workspace memory section when long-term memory is available.
            # TODO: append pinned instructions from conversation settings.
            # TODO: append workspace coding standards when standards store exists.
        )
        chat_messages = self._compose_chat_messages(messages, author_names)

        metadata: dict[str, Any] = {
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "conversation_id": str(conversation.id),
            "conversation_title": conversation.title,
            "participant_names": participant_names,
            # Reserved keys for future PromptBuilder sections (see TODOs above).
            "conversation_snapshot": None,
            "retrieved_documents": None,
            "code_context": None,
            "workspace_memory": None,
            "pinned_instructions": None,
            "coding_standards": None,
        }

        return PromptContext(
            system_prompt=system_prompt,
            chat_messages=chat_messages,
            metadata=metadata,
        )

    @staticmethod
    def _participant_names(participants: list[ConversationParticipant]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for participant in participants:
            if participant.user is None:
                continue
            name = participant.user.name.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
        return names

    @staticmethod
    def _compose_system_prompt(
        *,
        workspace_name: str,
        conversation_title: str,
        participant_names: list[str],
        base_system_prompt: str,
    ) -> str:
        participant_lines = "\n".join(f"- {name}" for name in participant_names) or "- (none)"
        metadata_block = "\n".join(
            [
                _METADATA_SEPARATOR,
                "",
                "Workspace:",
                workspace_name,
                "",
                "Conversation:",
                conversation_title,
                "",
                "Participants:",
                "",
                participant_lines,
                "",
                "You are collaborating with multiple users inside a shared conversation.",
                "",
                "Always pay attention to which participant sent each message.",
                "",
                _METADATA_SEPARATOR,
            ]
        )
        base = base_system_prompt.strip()
        if base:
            return f"{metadata_block}\n\n{base}"
        return metadata_block

    @staticmethod
    def _compose_chat_messages(
        messages: list[Message],
        author_names: dict[UUID, str],
    ) -> list[ChatMessage]:
        chat_messages: list[ChatMessage] = []
        for message in messages:
            if message.role == MessageRole.ASSISTANT:
                chat_messages.append(
                    ChatMessage(role="assistant", content=message.content),
                )
            elif message.role == MessageRole.USER:
                display_name = "Unknown"
                if message.author_id is not None:
                    display_name = author_names.get(message.author_id, "Unknown")
                content = f"[{display_name}]\n\n{message.content}"
                chat_messages.append(ChatMessage(role="user", content=content))
        return chat_messages
