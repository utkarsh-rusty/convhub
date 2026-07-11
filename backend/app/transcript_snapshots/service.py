from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript_chunk import TranscriptChunk
from app.models.transcript_snapshot import TranscriptSnapshot
from app.transcript_snapshots.schemas import (
    TranscriptSnapshotExportResponse,
    TranscriptSnapshotResponse,
)


class TranscriptSnapshotService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def rebuild_snapshot(
        self,
        external_ai_session_id: UUID,
        *,
        commit: bool = True,
    ) -> TranscriptSnapshot:
        chunks = await self._load_ordered_chunks(external_ai_session_id)
        self._validate_chunk_ordering(chunks)
        content = "".join(chunk.raw_content for chunk in chunks)
        character_count = len(content)

        snapshot = await self._get_snapshot_row(external_ai_session_id)
        if snapshot is None:
            snapshot = TranscriptSnapshot(
                external_ai_session_id=external_ai_session_id,
                snapshot_version=1,
                content=content,
                character_count=character_count,
            )
            self.db.add(snapshot)
        else:
            snapshot.snapshot_version = snapshot.snapshot_version + 1
            snapshot.content = content
            snapshot.character_count = character_count
            snapshot.updated_at = datetime.now(UTC)

        if commit:
            await self.db.commit()
            await self.db.refresh(snapshot)
        else:
            await self.db.flush()

        return snapshot

    async def ensure_snapshot(self, external_ai_session_id: UUID) -> TranscriptSnapshot:
        snapshot = await self._get_snapshot_row(external_ai_session_id)
        if snapshot is not None:
            return snapshot
        return await self.rebuild_snapshot(external_ai_session_id)

    async def get_snapshot(
        self,
        external_ai_session_id: UUID,
    ) -> TranscriptSnapshotResponse:
        snapshot = await self.ensure_snapshot(external_ai_session_id)
        return self._to_response(snapshot)

    async def export_markdown(
        self,
        external_ai_session_id: UUID,
    ) -> TranscriptSnapshotExportResponse:
        snapshot = await self.ensure_snapshot(external_ai_session_id)
        return TranscriptSnapshotExportResponse(
            filename=f"transcript-snapshot-{external_ai_session_id}.md",
            content=snapshot.content,
            content_type="text/markdown",
            snapshot_version=snapshot.snapshot_version,
            character_count=snapshot.character_count,
        )

    async def _get_snapshot_row(
        self,
        external_ai_session_id: UUID,
    ) -> TranscriptSnapshot | None:
        result = await self.db.execute(
            select(TranscriptSnapshot).where(
                TranscriptSnapshot.external_ai_session_id == external_ai_session_id
            )
        )
        return result.scalar_one_or_none()

    async def _load_ordered_chunks(
        self,
        external_ai_session_id: UUID,
    ) -> list[TranscriptChunk]:
        result = await self.db.execute(
            select(TranscriptChunk)
            .where(TranscriptChunk.external_ai_session_id == external_ai_session_id)
            .order_by(TranscriptChunk.sequence_number.asc(), TranscriptChunk.id.asc())
        )
        return list(result.scalars().all())

    def _validate_chunk_ordering(self, chunks: list[TranscriptChunk]) -> None:
        for index, chunk in enumerate(chunks, start=1):
            if chunk.sequence_number != index:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Transcript chunks are not contiguous; "
                        f"expected sequence_number {index}, got {chunk.sequence_number}"
                    ),
                )

    def _to_response(self, snapshot: TranscriptSnapshot) -> TranscriptSnapshotResponse:
        return TranscriptSnapshotResponse(
            id=snapshot.id,
            external_ai_session_id=snapshot.external_ai_session_id,
            snapshot_version=snapshot.snapshot_version,
            character_count=snapshot.character_count,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
        )
