"""Custom exceptions shared across services."""


class NoHealthyNodeError(Exception):
    """Raised by scheduler when no healthy inference node is available."""


class NodeNotFoundError(Exception):
    """Raised when a node_id is not registered."""


class AuthenticationError(Exception):
    """Raised on invalid credentials."""


class PermissionDeniedError(Exception):
    """Raised when a user lacks the required role."""
