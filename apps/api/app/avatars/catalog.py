"""Public, versioned identifiers; never accept arbitrary drawing instructions."""

import json
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, Field

CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text())
DEFAULT_AVATAR = CATALOG["default_id"]
AVATAR_IDS = frozenset(item["id"] for item in CATALOG["presets"])


def validate_avatar(value: str) -> str:
    if value not in AVATAR_IDS:
        raise ValueError("请选择内置头像")
    return value


AvatarID = Annotated[str, Field(min_length=1, max_length=32), AfterValidator(validate_avatar)]
