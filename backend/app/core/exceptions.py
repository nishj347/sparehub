"""Application HTTP exception class supporting structured error codes and field errors."""
from typing import Dict, Optional
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppHTTPException(StarletteHTTPException):
    """Custom HTTP exception carrying structured error codes, optional field name, and headers."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        field: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.field = field


AppError = AppHTTPException
