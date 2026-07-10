#!/usr/bin/env python3
"""Seed two test users with Sprint 27/28 sample data (direct SQL, no heavy ORM loads).

Usage:
  cd convhub/backend && PYTHONPATH=. python ../scripts/seed_sprint_test_users.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.password import hash_password

PASSWORD = "test12345"
DEV1_EMAIL = "dev1@example.com"
DEV2_EMAIL = "dev2@example.com"


async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.sqlalchemy_database_uri, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    now = datetime.now(UTC)
    pw = hash_password(PASSWORD)

    async with factory() as db:
        # --- users ---
        async def user_id(email: str, name: str) -> str:
            row = (
                await db.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})
            ).first()
            if row:
                return str(row[0])
            uid = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO users (id, email, name, password_hash, created_at, updated_at)
                    VALUES (:id, :email, :name, :pw, :now, :now)
                    """
                ),
                {"id": uid, "email": email, "name": name, "pw": pw, "now": now},
            )
            return uid

        print("users…", flush=True)
        u1 = await user_id(DEV1_EMAIL, "Dev One")
        u2 = await user_id(DEV2_EMAIL, "Dev Two")

        # --- workspace ---
        print("workspace…", flush=True)
        row = (
            await db.execute(text("SELECT id FROM workspaces WHERE slug = 'sprint-lab'"))
        ).first()
        if row:
            ws = str(row[0])
        else:
            ws = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO workspaces (id, name, slug, owner_id, created_at, updated_at)
                    VALUES (:id, 'Sprint Lab', 'sprint-lab', :owner, :now, :now)
                    """
                ),
                {"id": ws, "owner": u1, "now": now},
            )

        async def ensure_member(user_id: str, role: str) -> None:
            exists = (
                await db.execute(
                    text(
                        """
                        SELECT 1 FROM workspace_members
                        WHERE workspace_id = :ws AND user_id = :u
                        """
                    ),
                    {"ws": ws, "u": user_id},
                )
            ).first()
            if exists:
                return
            await db.execute(
                text(
                    """
                    INSERT INTO workspace_members
                      (id, workspace_id, user_id, role, created_at, updated_at)
                    VALUES (:id, :ws, :u, :role, :now, :now)
                    """
                ),
                {"id": str(uuid4()), "ws": ws, "u": user_id, "role": role, "now": now},
            )
            # budgets / lending prefs if tables exist
            try:
                await db.execute(
                    text(
                        """
                        INSERT INTO user_budgets
                          (id, workspace_id, user_id, monthly_credit_limit, remaining_credits,
                           used_credits, created_at, updated_at)
                        VALUES (:id, :ws, :u, 5000, 5000, 0, :now, :now)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"id": str(uuid4()), "ws": ws, "u": user_id, "now": now},
                )
            except Exception:
                await db.rollback()
                # re-open transaction context by beginning again via commit path
                raise

        # Simpler: just members; budgets created lazily by app
        for uid, role in ((u1, "owner"), (u2, "member")):
            exists = (
                await db.execute(
                    text(
                        "SELECT 1 FROM workspace_members WHERE workspace_id=:ws AND user_id=:u"
                    ),
                    {"ws": ws, "u": uid},
                )
            ).first()
            if not exists:
                await db.execute(
                    text(
                        """
                        INSERT INTO workspace_members
                          (id, workspace_id, user_id, role, created_at, updated_at)
                        VALUES (:id, :ws, :u, CAST(:role AS workspace_role), :now, :now)
                        """
                    ),
                    {"id": str(uuid4()), "ws": ws, "u": uid, "role": role, "now": now},
                )

        # workspace budget settings
        exists = (
            await db.execute(
                text("SELECT 1 FROM workspace_budget_settings WHERE workspace_id = :ws"),
                {"ws": ws},
            )
        ).first()
        if not exists:
            await db.execute(
                text(
                    """
                    INSERT INTO workspace_budget_settings
                      (id, workspace_id, allow_credit_borrowing, allow_emergency_pool,
                       allow_local_models, hard_budget_enforcement, created_at, updated_at)
                    VALUES (:id, :ws, true, false, true, true, :now, :now)
                    """
                ),
                {"id": str(uuid4()), "ws": ws, "now": now},
            )

        for uid in (u1, u2):
            exists = (
                await db.execute(
                    text(
                        "SELECT 1 FROM user_budgets WHERE workspace_id=:ws AND user_id=:u"
                    ),
                    {"ws": ws, "u": uid},
                )
            ).first()
            if not exists:
                await db.execute(
                    text(
                        """
                        INSERT INTO user_budgets
                          (id, workspace_id, user_id, monthly_credit_limit, remaining_credits,
                           used_credits, borrowed_credits, lent_credits, reset_date,
                           created_at, updated_at)
                        VALUES (:id, :ws, :u, 5000, 5000, 0, 0, 0, CURRENT_DATE, :now, :now)
                        """
                    ),
                    {"id": str(uuid4()), "ws": ws, "u": uid, "now": now},
                )
            exists = (
                await db.execute(
                    text(
                        "SELECT 1 FROM lending_preferences WHERE workspace_id=:ws AND user_id=:u"
                    ),
                    {"ws": ws, "u": uid},
                )
            ).first()
            if not exists:
                await db.execute(
                    text(
                        """
                        INSERT INTO lending_preferences
                          (id, workspace_id, user_id, auto_share_enabled,
                           monthly_share_limit, minimum_reserved_credits, priority,
                           created_at, updated_at)
                        VALUES (:id, :ws, :u, false, 0, 500, 0, :now, :now)
                        """
                    ),
                    {"id": str(uuid4()), "ws": ws, "u": uid, "now": now},
                )

        # --- project ---
        print("project…", flush=True)
        row = (
            await db.execute(
                text(
                    "SELECT id FROM projects WHERE workspace_id=:ws AND name='Sync & Sessions'"
                ),
                {"ws": ws},
            )
        ).first()
        if row:
            project_id = str(row[0])
        else:
            project_id = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO projects
                      (id, workspace_id, name, description, created_by_id, created_at, updated_at)
                    VALUES (:id, :ws, 'Sync & Sessions', 'Lab for Sprint 27/28', :u, :now, :now)
                    """
                ),
                {"id": project_id, "ws": ws, "u": u1, "now": now},
            )

        # --- repository ---
        print("repository…", flush=True)
        row = (
            await db.execute(
                text(
                    "SELECT id FROM repositories WHERE workspace_id=:ws AND name='convhub-lab'"
                ),
                {"ws": ws},
            )
        ).first()
        if row:
            repo_id = str(row[0])
        else:
            repo_id = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO repositories
                      (id, workspace_id, project_id, name, provider, owner, repository_name,
                       remote_url, default_branch, visibility, is_active, created_by_id,
                       created_at, updated_at)
                    VALUES
                      (:id, :ws, :project, 'convhub-lab', 'github', 'convhub', 'lab',
                       'https://github.com/convhub/lab', 'main', 'private', true, :u,
                       :now, :now)
                    """
                ),
                {"id": repo_id, "ws": ws, "project": project_id, "u": u1, "now": now},
            )

        async def ensure_branch(name: str, is_default: bool) -> str:
            row = (
                await db.execute(
                    text(
                        """
                        SELECT id FROM repository_branches
                        WHERE repository_id=:r AND name=:n
                        """
                    ),
                    {"r": repo_id, "n": name},
                )
            ).first()
            if row:
                return str(row[0])
            bid = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO repository_branches
                      (id, repository_id, name, is_default, is_active, created_at, updated_at)
                    VALUES (:id, :r, :n, :d, true, :now, :now)
                    """
                ),
                {"id": bid, "r": repo_id, "n": name, "d": is_default, "now": now},
            )
            # branch memory + init sync record
            mid = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO branch_memories
                      (id, repository_branch_id, memory_version, current_sync_version,
                       sync_status, created_at, updated_at)
                    VALUES (:id, :b, 0, 0, 'not_synced', :now, :now)
                    """
                ),
                {"id": mid, "b": bid, "now": now},
            )
            rid = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO branch_sync_records
                      (id, branch_memory_id, sync_type, sync_version, notes, created_at)
                    VALUES (:id, :m, 'attach_repository', 1, 'Branch memory initialized', :now)
                    """
                ),
                {"id": rid, "m": mid, "now": now},
            )
            await db.execute(
                text(
                    """
                    UPDATE branch_memories
                    SET memory_version = 1, current_sync_version = 1,
                        latest_sync_record_id = :r
                    WHERE id = :m
                    """
                ),
                {"r": rid, "m": mid},
            )
            return bid

        print("branches…", flush=True)
        main_id = await ensure_branch("main", True)
        feature_id = await ensure_branch("feature/sync-demo", False)

        async def make_conversation(
            *,
            user_id: str,
            title: str,
            message: str,
            commit_title: str,
            branch_id: str,
        ) -> tuple[str, str]:
            cid = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO conversations
                      (id, workspace_id, project_id, coding_enabled, repository_id,
                       created_by_id, owner_id, title, last_activity_at, created_at, updated_at)
                    VALUES
                      (:id, :ws, :project, true, :repo, :u, :u, :title, :now, :now, :now)
                    """
                ),
                {
                    "id": cid,
                    "ws": ws,
                    "project": project_id,
                    "repo": repo_id,
                    "u": user_id,
                    "title": title,
                    "now": now,
                },
            )
            await db.execute(
                text(
                    """
                    INSERT INTO conversation_participants
                      (conversation_id, user_id, role, joined_at)
                    VALUES (:c, :u, CAST('owner' AS conversation_participant_role), :now)
                    """
                ),
                {"c": cid, "u": user_id, "now": now},
            )
            mid = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO messages
                      (id, conversation_id, author_id, role, content, created_at)
                    VALUES (:id, :c, :u, 'user', :content, :now)
                    """
                ),
                {"id": mid, "c": cid, "u": user_id, "content": message, "now": now},
            )
            ckpt = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO conversation_checkpoints
                      (id, conversation_id, latest_message_id, created_at)
                    VALUES (:id, :c, :m, :now)
                    """
                ),
                {"id": ckpt, "c": cid, "m": mid, "now": now},
            )
            commit_id = str(uuid4())
            commit_hash = uuid4().hex[:7]
            await db.execute(
                text(
                    """
                    INSERT INTO conversation_commits
                      (id, commit_hash, conversation_id, checkpoint_id, latest_message_id,
                       title, created_by_id, created_at)
                    VALUES (:id, :hash, :c, :ckpt, :m, :title, :u, :now)
                    """
                ),
                {
                    "id": commit_id,
                    "hash": commit_hash,
                    "c": cid,
                    "ckpt": ckpt,
                    "m": mid,
                    "title": commit_title,
                    "u": user_id,
                    "now": now,
                },
            )
            pkg_id = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO context_packages
                      (id, commit_id, conversation_id, version, status, generated_at,
                       metadata_json, summary_json, statistics_json, search_keywords_json)
                    VALUES
                      (:id, :commit, :c, 1, 'generated', :now,
                       '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb)
                    """
                ),
                {"id": pkg_id, "commit": commit_id, "c": cid, "now": now},
            )

            # append LOCAL_COMMIT sync record on branch memory
            mem = (
                await db.execute(
                    text(
                        "SELECT id, memory_version FROM branch_memories WHERE repository_branch_id=:b"
                    ),
                    {"b": branch_id},
                )
            ).first()
            assert mem is not None
            memory_id, version = str(mem[0]), int(mem[1]) + 1
            sync_id = str(uuid4())
            await db.execute(
                text(
                    """
                    INSERT INTO branch_sync_records
                      (id, branch_memory_id, conversation_id, commit_id, context_package_id,
                       user_id, sync_type, sync_version, notes, created_at)
                    VALUES
                      (:id, :m, :c, :commit, :pkg, :u, 'local_commit', :v, :notes, :now)
                    """
                ),
                {
                    "id": sync_id,
                    "m": memory_id,
                    "c": cid,
                    "commit": commit_id,
                    "pkg": pkg_id,
                    "u": user_id,
                    "v": version,
                    "notes": commit_title,
                    "now": now,
                },
            )
            await db.execute(
                text(
                    """
                    UPDATE branch_memories
                    SET memory_version = :v, current_sync_version = :v,
                        latest_sync_record_id = :s, updated_at = :now
                    WHERE id = :m
                    """
                ),
                {"v": version, "s": sync_id, "now": now, "m": memory_id},
            )
            return cid, commit_id

        print("conversations…", flush=True)
        conv1, commit1 = await make_conversation(
            user_id=u1,
            title="Auth refactor discussion",
            message="Let's plan the Sync API push/pull flow for plugins.",
            commit_title="Sync API planning checkpoint",
            branch_id=main_id,
        )
        conv2, commit2 = await make_conversation(
            user_id=u2,
            title="Workspace session smoke test",
            message="Opening a developer workspace session from VS Code.",
            commit_title="Session heartbeat checkpoint",
            branch_id=feature_id,
        )

        # Sprint 27 — PLUGIN_PUSH on main
        print("sync push…", flush=True)
        mem = (
            await db.execute(
                text(
                    "SELECT id, memory_version, latest_sync_record_id FROM branch_memories WHERE repository_branch_id=:b"
                ),
                {"b": main_id},
            )
        ).first()
        assert mem is not None
        memory_id, version = str(mem[0]), int(mem[1]) + 1
        latest = (
            await db.execute(
                text(
                    """
                    SELECT conversation_id, commit_id, context_package_id
                    FROM branch_sync_records WHERE id = :id
                    """
                ),
                {"id": str(mem[2])},
            )
        ).first()
        push_id = str(uuid4())
        await db.execute(
            text(
                """
                INSERT INTO branch_sync_records
                  (id, branch_memory_id, conversation_id, commit_id, context_package_id,
                   user_id, sync_type, sync_version, notes, created_at)
                VALUES
                  (:id, :m, :c, :commit, :pkg, :u, 'plugin_push', :v,
                   'Seeded PLUGIN_PUSH for Sprint 27 testing', :now)
                """
            ),
            {
                "id": push_id,
                "m": memory_id,
                "c": str(latest[0]) if latest else conv1,
                "commit": str(latest[1]) if latest and latest[1] else commit1,
                "pkg": str(latest[2]) if latest and latest[2] else None,
                "u": u1,
                "v": version,
                "now": now,
            },
        )
        await db.execute(
            text(
                """
                UPDATE branch_memories
                SET memory_version = :v, current_sync_version = :v,
                    latest_sync_record_id = :s, last_sync_at = :now,
                    sync_status = 'ready', updated_at = :now
                WHERE id = :m
                """
            ),
            {"v": version, "s": push_id, "now": now, "m": memory_id},
        )

        # Sprint 28 — workspace sessions
        print("workspace sessions…", flush=True)
        for user_id, branch_id, conv_id, client, version_str in (
            (u1, main_id, conv1, "vscode", "1.95.0"),
            (u2, feature_id, conv2, "cursor", "0.45.0"),
        ):
            await db.execute(
                text(
                    """
                    INSERT INTO developer_workspace_sessions
                      (id, workspace_id, project_id, repository_id, repository_branch_id,
                       conversation_id, user_id, status, started_at, last_heartbeat_at,
                       client_name, client_version, platform, working_directory,
                       created_at, updated_at)
                    VALUES
                      (:id, :ws, :project, :repo, :branch, :conv, :u, 'active',
                       :now, :now, :client, :ver, 'darwin', :wd, :now, :now)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "ws": ws,
                    "project": project_id,
                    "repo": repo_id,
                    "branch": branch_id,
                    "conv": conv_id,
                    "u": user_id,
                    "now": now,
                    "client": client,
                    "ver": version_str,
                    "wd": f"/Users/{client}/convhub-lab",
                },
            )

        await db.commit()

        print()
        print("=" * 60)
        print("LOGIN CREDENTIALS")
        print("=" * 60)
        print(f"  Dev One  {DEV1_EMAIL}  /  {PASSWORD}  (workspace owner)")
        print(f"  Dev Two  {DEV2_EMAIL}  /  {PASSWORD}  (workspace member)")
        print()
        print("  Workspace : Sprint Lab")
        print("  Project   : Sync & Sessions")
        print("  Repository: convhub-lab")
        print("  Branches  : main , feature/sync-demo")
        print(f"  Conv One  : {conv1}")
        print(f"  Conv Two  : {conv2}")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
