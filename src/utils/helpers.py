"""
helpers.py - Miscellaneous helper functions for the Semantic Extraction Arena.
"""

import os
from typing import Any
import base64

_MIME_TYPES = {
    ".svg":  "image/svg+xml",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

def get_image_base64(image_path: str) -> str:
    """Read an image file and return a data URI (base64-encoded) string.

    The returned string can be used directly as an ``<img src>`` value.
    """
    ext = os.path.splitext(image_path)[1].lower()
    mime = _MIME_TYPES.get(ext, "image/png")
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"

def _json_depth(obj: Any, level: int = 0) -> int:
    """Recursively calculate the maximum depth of a JSON object/list."""
    if isinstance(obj, dict) and obj:
        return max((_json_depth(v, level + 1) for v in obj.values()), default=level)
    if isinstance(obj, list) and obj:
        return max((_json_depth(v, level + 1) for v in obj), default=level)
    return level


def calculate_metrics(data: Any) -> dict:
    """Return data richness metrics (size, fields, structural depth)."""
    text = str(data)
    is_collection = isinstance(data, (dict, list))
    return {
        "word_count": len(text.split()),
        "char_count": len(text),
        "field_count": len(data) if is_collection else 0,
        "json_depth": _json_depth(data) if is_collection else 0,
    }
