from pathlib import Path

from app.content.media import media_paths, resolve_media_path
from app.content.models import ContentRevision
from app.learning.service import view


async def session_content(db, row):
    result = []
    for source in row.sources:
        if "container_id" not in source:
            continue
        revision = await db.get(ContentRevision, (source["container_id"], source["version"]))
        if revision:
            result.append(revision.public_payload)
    return result


async def authorized_media(db, student, row, public_root: Path, requested: str):
    allowed = media_paths(await session_content(db, row))
    current = await view(db, row, student)
    allowed |= media_paths(current.get("question"))
    allowed |= media_paths(current.get("feedback"))
    return resolve_media_path(public_root, requested, allowed)
