class DomainError(Exception):
    """Base domain exception."""


class ValidationError(DomainError):
    """Raised when domain invariants are violated."""


class NotFoundError(DomainError):
    """Raised when required entities are unavailable."""
