"""Workspace and invitation API QA tests."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    AuthContext,
    WorkspaceContext,
    create_workspace,
    invite_and_accept,
)


@pytest.mark.asyncio
async def test_create_and_list_workspaces(client: AsyncClient, auth_user: AuthContext) -> None:
    created = await create_workspace(client, auth_user, name="QA Workspace")
    listed = await client.get("/workspaces", headers=auth_user.headers)
    assert listed.status_code == 200
    ids = [workspace["id"] for workspace in listed.json()]
    assert created.workspace_id in ids


@pytest.mark.asyncio
async def test_get_workspace_detail(client: AsyncClient, workspace: WorkspaceContext) -> None:
    response = await client.get(
        f"/workspaces/{workspace.workspace_id}",
        headers=workspace.headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "owner"


@pytest.mark.asyncio
async def test_non_member_cannot_access_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    response = await client.get(
        f"/workspaces/{workspace.workspace_id}",
        headers=second_user.headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_member_cannot_update_workspace(
    client: AsyncClient,
    member_workspace: tuple[WorkspaceContext, AuthContext],
) -> None:
    workspace, member = member_workspace
    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}",
        headers=member.headers,
        json={"name": "Renamed"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_update_workspace(client: AsyncClient, workspace: WorkspaceContext) -> None:
    response = await client.patch(
        f"/workspaces/{workspace.workspace_id}",
        headers=workspace.headers,
        json={"name": "Updated Workspace"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workspace"


@pytest.mark.asyncio
async def test_admin_cannot_delete_workspace(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": second_user.email, "role": "admin"},
    )
    assert invite.status_code == 201
    accept = await client.post(
        f"/invitations/{invite.json()['token']}/accept",
        headers=second_user.headers,
    )
    assert accept.status_code == 200

    admin_headers = {**second_user.headers}
    delete = await client.delete(
        f"/workspaces/{workspace.workspace_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_delete_workspace(client: AsyncClient, auth_user: AuthContext) -> None:
    workspace = await create_workspace(client, auth_user)
    response = await client.delete(
        f"/workspaces/{workspace.workspace_id}",
        headers=workspace.headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_invite_member_happy_path(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    await invite_and_accept(client, workspace, second_user)
    members = await client.get(
        f"/workspaces/{workspace.workspace_id}/members",
        headers=workspace.headers,
    )
    assert members.status_code == 200
    emails = [member["email"] for member in members.json()]
    assert second_user.email in emails


@pytest.mark.asyncio
async def test_member_cannot_invite(client: AsyncClient, member_workspace) -> None:
    workspace, member = member_workspace
    response = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=member.headers,
        json={"email": f"guest-{uuid4().hex}@example.com", "role": "member"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_invite_returns_409(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    email = f"pending-{uuid4().hex}@example.com"
    first = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": email, "role": "member"},
    )
    assert first.status_code == 201
    second = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": email, "role": "member"},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_accept_invitation_wrong_email_returns_403(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": f"someone-else-{uuid4().hex}@example.com", "role": "member"},
    )
    assert invite.status_code == 201
    response = await client.post(
        f"/invitations/{invite.json()['token']}/accept",
        headers=second_user.headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_accept_invitation_twice_returns_400(
    client: AsyncClient,
    workspace: WorkspaceContext,
    second_user: AuthContext,
) -> None:
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": second_user.email, "role": "member"},
    )
    token = invite.json()["token"]
    first = await client.post(f"/invitations/{token}/accept", headers=second_user.headers)
    assert first.status_code == 200
    second = await client.post(f"/invitations/{token}/accept", headers=second_user.headers)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_list_pending_invitations_admin_only(
    client: AsyncClient,
    workspace: WorkspaceContext,
    member_workspace,
) -> None:
    email = f"pending-list-{uuid4().hex}@example.com"
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": email, "role": "member"},
    )
    assert invite.status_code == 201

    admin_list = await client.get(
        f"/workspaces/{workspace.workspace_id}/invitations",
        headers=workspace.headers,
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1

    _, member = member_workspace
    member_list = await client.get(
        f"/workspaces/{workspace.workspace_id}/invitations",
        headers=member.headers,
    )
    assert member_list.status_code == 403


@pytest.mark.asyncio
async def test_refresh_invitation_link(
    client: AsyncClient,
    workspace: WorkspaceContext,
) -> None:
    invite = await client.post(
        f"/workspaces/{workspace.workspace_id}/invite",
        headers=workspace.headers,
        json={"email": f"refresh-{uuid4().hex}@example.com", "role": "member"},
    )
    invitation_id = (
        await client.get(
            f"/workspaces/{workspace.workspace_id}/invitations",
            headers=workspace.headers,
        )
    ).json()[0]["id"]

    refreshed = await client.post(
        f"/workspaces/{workspace.workspace_id}/invitations/{invitation_id}/link",
        headers=workspace.headers,
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["token"]
    assert refreshed.json()["token"] != invite.json()["token"]


@pytest.mark.asyncio
async def test_invitation_preview_invalid_token(client: AsyncClient) -> None:
    response = await client.get("/invitations/not-a-valid-token")
    assert response.status_code == 200
    assert response.json()["is_valid"] is False
