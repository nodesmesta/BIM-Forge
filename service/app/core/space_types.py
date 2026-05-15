from enum import Enum
from typing import Any


def canonical_space_type_key(space_type: Any) -> str:
    if isinstance(space_type, Enum):
        return str(space_type.value).lower()
    s = str(space_type).strip()
    if s.startswith("RoomType."):
        return s.split(".", 1)[1].lower()
    return s.lower()
