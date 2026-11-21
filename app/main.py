# Command to run:
# uvicorn app.main:app --reload
# http://127.0.0.1:8000/restaurants

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, cart, checkout, customers, menus, orders, restaurants
from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    DataAccessError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.schemas.common import HealthResponse

STATIC_DIR = Path(__file__).resolve().parent / "static" 


app = FastAPI()


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """Convert application errors into consistent HTTP responses."""

    status_codes = {
        UnauthorizedError: 401,
        ForbiddenError: 403,
        NotFoundError: 404,
        BusinessRuleError: 422,
        ConflictError: 409,
        DataAccessError: 500,
    }

    status_code = next(
        (
            status
            for error_type, status in status_codes.items()
            if isinstance(exc, error_type)
        ),
        500,
    )

    # Never expose raw storage errors to clients.
    detail = (
        "Could not access application data"
        if isinstance(exc, DataAccessError)
        else str(exc)
    )

    headers = (
        {"WWW-Authenticate": "Bearer"}
        if status_code == 401
        else None
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "code": exc.code,
        },
        headers=headers,
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)    #modified to exclude route from API docs since its a webpage not endpoint
def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/owner", include_in_schema=False)
def owner_page():
    return FileResponse(STATIC_DIR / "owner.html")

@app.get("/account", include_in_schema=False)
def account_page():
    return FileResponse(STATIC_DIR / "account.html")

@app.get("/health", response_model=HealthResponse, summary="Health check")
def health():
    """Returns `{"status": "ok"}` when the API is running. Has no parameters and no error responses."""
    return {"status": "ok"}


app.include_router(restaurants.router)
app.include_router(menus.router)
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(cart.router)
app.include_router(checkout.router)
app.include_router(orders.router)
