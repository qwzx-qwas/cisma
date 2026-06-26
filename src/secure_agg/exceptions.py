"""Project-specific exception types."""


class SecureAggregationError(Exception):
    """Base class for secure aggregation errors."""


class DimensionMismatchError(SecureAggregationError):
    """Raised when vectors with incompatible dimensions are provided."""


class EncodingError(SecureAggregationError):
    """Raised when a floating-point value cannot be encoded safely."""


class EncodingOverflowError(EncodingError):
    """Raised when an encoded value would exceed the supported field range."""


class InvalidShareError(SecureAggregationError):
    """Raised when secret share data is malformed or incomplete."""


class DuplicateMessageError(SecureAggregationError):
    """Raised when a participant submits the same message more than once."""


class UnknownParticipantError(SecureAggregationError):
    """Raised when a message references an unregistered participant."""


class InvalidRoundStateError(SecureAggregationError):
    """Raised when an operation is not allowed in the round's current state."""


class CommunicationError(SecureAggregationError):
    """Raised when network communication fails."""


class RoundTimeoutError(SecureAggregationError):
    """Raised when a round does not complete before its deadline."""
