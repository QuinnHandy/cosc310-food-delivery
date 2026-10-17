from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error body returned for 404 and 500 responses."""

    detail: str = Field(description="Human-readable explanation of the error.")


class HealthResponse(BaseModel):
    """Health check result."""

    status: str = Field(description='Always "ok" when the API is running.')
