from typing import Any, NoReturn

from fastapi import HTTPException, status


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = status.HTTP_404_NOT_FOUND,
) -> NoReturn:
    """Raise an HTTPException with a consistent JSON error envelope.

    The response body follows the format::

        {"error": {"code": "...", "message": "...", "details": {...}}}

    Use this in route handlers and service methods to guarantee every error
    response has the same structure, making client-side error handling
    predictable.

    Args:
        code: Machine-readable error code (e.g. "NOT_FOUND", "VALIDATION_ERROR").
        message: Human-readable error description.
        details: Optional dictionary with additional context (e.g. the field that
            failed validation, the ID that was not found).
        status_code: HTTP status code (default 404).
    """
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )
