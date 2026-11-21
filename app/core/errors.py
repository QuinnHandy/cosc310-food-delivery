"""Shared domain exceptions for consistent API error handling."""


class DomainError(Exception):
    """Base exception for expected application errors."""

    code = "domain_error"


class NotFoundError(DomainError):
    """A requested resource does not exist."""

    code = "not_found"


class ConflictError(DomainError):
    """An operation conflicts with the current application state."""

    code = "conflict"


class ForbiddenError(DomainError):
    """The user is not permitted to perform an operation."""

    code = "forbidden"


class UnauthorizedError(DomainError):
    """Authentication is missing or invalid."""

    code = "unauthorized"


class BusinessRuleError(DomainError):
    """An operation violates a business rule."""

    code = "business_rule"


class DataAccessError(DomainError):
    """Stored application data could not be read or written."""

    code = "data_access_error"
