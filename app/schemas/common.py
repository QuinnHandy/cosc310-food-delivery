from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard response body for domain errors."""

    detail: str = Field(description="Human-readable explanation of the error.")
    code: str = Field(description="Machine-readable error code.")


class HealthResponse(BaseModel):
    """Health check result."""

    status: str = Field(description='Always "ok" when the API is running.')
