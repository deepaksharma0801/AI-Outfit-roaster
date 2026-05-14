from fastapi import HTTPException, status


class ImageValidationError(ValueError):
    """Raised when an uploaded image fails validation."""


def bad_upload(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
