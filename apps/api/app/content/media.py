from pathlib import Path
from urllib.parse import unquote, urlsplit

from app.errors import APIError


def media_paths(value):
    prefixes = ("/audio/", "/story-images/", "/textbook-pages/")
    if isinstance(value, str) and value.startswith(prefixes):
        return {value}
    if isinstance(value, dict):
        return set().union(*(media_paths(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(media_paths(v) for v in value)) if value else set()
    return set()


def resolve_media_path(public_root: Path, requested: str, allowed: set[str]):
    if requested not in allowed:
        raise APIError(404, "MEDIA_NOT_FOUND", "找不到当前阶段可访问的媒体")
    parsed = urlsplit(requested)
    root = public_root.resolve()
    target = (root / unquote(parsed.path).lstrip("/")).resolve()
    extensions = {".mp3", ".opus", ".ogg", ".wav", ".png", ".jpg", ".jpeg", ".webp"}
    if (
        parsed.scheme
        or parsed.netloc
        or not target.is_relative_to(root)
        or target.suffix.lower() not in extensions
        or not target.is_file()
    ):
        raise APIError(404, "MEDIA_NOT_FOUND", "媒体尚未安装或不可用")
    return target
