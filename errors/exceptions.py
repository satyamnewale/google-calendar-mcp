class CalendarError(Exception):
    """Base exception for Google Calendar MCP."""

    code = "CALENDAR_ERROR"
    retryable = False


class EventNotFoundError(CalendarError):
    code = "EVENT_NOT_FOUND"


class EventAlreadyCancelledError(CalendarError):
    code = "EVENT_ALREADY_CANCELLED"


class EventConflictError(CalendarError):
    code = "EVENT_CONFLICT"


class InvalidEventError(CalendarError):
    code = "INVALID_EVENT"


class InvalidDateRangeError(CalendarError):
    code = "INVALID_DATE_RANGE"


class ConfirmationRequiredError(CalendarError):
    code = "CONFIRMATION_REQUIRED"


class InvalidRecurrenceError(CalendarError):
    code = "INVALID_RECURRENCE"


class CalendarAuthenticationError(CalendarError):
    code = "AUTHENTICATION_REQUIRED"


class CalendarPermissionError(CalendarError):
    code = "INSUFFICIENT_PERMISSIONS"


class CalendarQuotaExceededError(CalendarError):
    code = "API_QUOTA_EXCEEDED"
    retryable = True


class CalendarServiceUnavailableError(CalendarError):
    code = "CALENDAR_SERVICE_UNAVAILABLE"
    retryable = True


class CalendarNetworkError(CalendarError):
    code = "NETWORK_ERROR"
    retryable = True