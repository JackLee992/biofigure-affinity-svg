class BiofigureError(RuntimeError):
    """Base error for expected user-facing failures."""


class ManifestError(BiofigureError):
    """Raised when a project manifest is invalid."""


class DependencyError(BiofigureError):
    """Raised when a required external dependency is unavailable."""


class QAError(BiofigureError):
    """Raised when an artifact fails a release gate."""
