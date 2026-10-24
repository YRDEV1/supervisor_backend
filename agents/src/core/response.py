from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class CustomResponse(JSONResponse):
    """Returns payload as-is; None gives empty body."""

    def __init__(self, content: Any = None, status_code: int = 200):
        super().__init__(content=jsonable_encoder(content), status_code=status_code)

    def render(self, content: Any) -> bytes:
        if content is None:
            return b""
        return super().render(content)
