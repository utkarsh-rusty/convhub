"""HTTP client for existing ConvHub APIs used by the Claude plugin."""

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
        return self._request_json("POST", "/external-ai-sessions/connect", payload)

    def upload_chunk(
        self,
        *,
        session_id: str,
        sequence_number: int,
        start_offset: int,
        end_offset: int,
        raw_content: str,
    ) -> dict[str, Any]:
        return self._request_json(
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
        return self._request_json(
            "POST",
            "/external-ai-sessions/disconnect",
            {"session_id": session_id},
        )

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/external-ai-sessions/{session_id}")

    def get_snapshot(self, session_id: str) -> dict[str, Any]:
        return self._request_json("GET", f"/external-ai-sessions/{session_id}/snapshot")

    def get_repository_memory(self, repository_branch_id: str | None = None) -> dict[str, Any]:
        branch_id = repository_branch_id or self.config.repository_branch_id
        return self._request_json("GET", f"/repository-branches/{branch_id}/repository-memory")

    def get_pull_package(self, repository_branch_id: str | None = None) -> dict[str, Any]:
        branch_id = repository_branch_id or self.config.repository_branch_id
        return self._request_json("GET", f"/repository-branches/{branch_id}/pull-package")

    def get_claude_handoff(self, repository_branch_id: str | None = None) -> str:
        branch_id = repository_branch_id or self.config.repository_branch_id
        return self._request_text("GET", f"/repository-branches/{branch_id}/handoff/claude")

    def _headers(self, *, accept: str = "application/json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "X-Workspace-ID": self.config.workspace_id,
            "Accept": accept,
        }

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = self._request_bytes(
            method,
            path,
            payload=payload,
            accept="application/json",
        )
        return json.loads(body.decode("utf-8")) if body else {}

    def _request_text(self, method: str, path: str) -> str:
        body = self._request_bytes(
            method,
            path,
            payload=None,
            accept="text/markdown, text/plain, */*",
        )
        return body.decode("utf-8")

    def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None,
        accept: str,
    ) -> bytes:
        url = f"{self.api_base}{path}"
        data = None
        headers = self._headers(accept=accept)
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ConvHubClientError(
                f"ConvHub API {method} {path} failed with {exc.code}: {body}",
                status=exc.code,
                body=body,
            ) from exc
        except urllib.error.URLError as exc:
            raise ConvHubClientError(f"ConvHub API unreachable: {exc}") from exc
