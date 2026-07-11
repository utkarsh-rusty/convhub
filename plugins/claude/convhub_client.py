"""HTTP client for existing ConvHub External AI Session APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from config import PluginConfig


class ConvHubClientError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def _normalize_api_base(server_url: str) -> str:
    base = server_url.rstrip("/")
    if base.endswith("/api/v1"):
        return base
    return f"{base}/api/v1"


class ConvHubClient:
    def __init__(self, config: PluginConfig) -> None:
        self.config = config
        self.api_base = _normalize_api_base(config.server_url)

    def connect(
        self,
        *,
        provider: str = "claude_code",
        machine_identifier: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": provider,
            "repository_id": self.config.repository_id,
            "repository_branch_id": self.config.repository_branch_id,
            "machine_identifier": machine_identifier,
        }
        conversation = conversation_id or self.config.conversation_id
        if conversation:
            payload["conversation_id"] = conversation
        return self._request("POST", "/external-ai-sessions/connect", payload)

    def upload_chunk(
        self,
        *,
        session_id: str,
        sequence_number: int,
        start_offset: int,
        end_offset: int,
        raw_content: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/external-ai-sessions/upload",
            {
                "session_id": session_id,
                "sequence_number": sequence_number,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "raw_content": raw_content,
            },
        )

    def disconnect(self, session_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/external-ai-sessions/disconnect",
            {"session_id": session_id},
        )

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.config.api_token}",
                "X-Workspace-ID": self.config.workspace_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ConvHubClientError(
                f"ConvHub API {method} {path} failed with {exc.code}: {body}",
                status=exc.code,
                body=body,
            ) from exc
        except urllib.error.URLError as exc:
            raise ConvHubClientError(f"ConvHub API unreachable: {exc}") from exc
