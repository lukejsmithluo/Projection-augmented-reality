from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AIImageEditResponse(BaseModel):
    accepted: bool
    output_file: Optional[str] = None
    error_code: Optional[str] = None
    error: Optional[str] = None