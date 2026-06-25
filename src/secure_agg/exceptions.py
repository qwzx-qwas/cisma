"""Project-specific exception types."""


class SecureAggregationError(Exception):
    """Base class for secure aggregation errors."""


class DimensionMismatchError(SecureAggregationError):
    """Raised when vectors with incompatible dimensions are provided."""


class EncodingError(SecureAggregationError):
    """Raised when a floating-point value cannot be encoded safely."""


class EncodingOverflowError(EncodingError):
    """Raised when an encoded value would exceed the supported field range."""
