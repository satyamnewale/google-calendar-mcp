import json
import logging

from functools import wraps

from pydantic import ValidationError
from googleapiclient.errors import HttpError
from google.auth.exceptions import (
    RefreshError,
    GoogleAuthError,
)

from fastmcp.exceptions import ToolError

from errors.exceptions import (
    CalendarError,
    EventNotFoundError,
    EventAlreadyCancelledError,
    EventConflictError,
    ConfirmationRequiredError,
    CalendarAuthenticationError,
    CalendarPermissionError,
    CalendarQuotaExceededError,
    CalendarServiceUnavailableError,
    CalendarNetworkError,
)


logger = logging.getLogger("google_calendar_mcp")


def create_error_response(
    code: str,
    message: str,
    action: str,
    retryable: bool = False,
) -> str:
    """Create a consistent error response for external MCP clients."""

    return json.dumps(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "action": action,
                "retryable": retryable,
            },
        },
        ensure_ascii=False,
    )


def handle_validation_error(exc: ValidationError) -> str:
    """Convert Pydantic validation errors into readable instructions."""

    issues = []

    for error in exc.errors():
        field = ".".join(str(item) for item in error["loc"])
        error_type = error["type"]

        if error_type == "missing":
            message = f"'{field}' is required."

        elif error_type == "string_too_short":
            message = f"'{field}' cannot be empty."

        elif error_type == "string_too_long":
            message = f"'{field}' exceeds the allowed length."

        elif error_type in {"greater_than", "greater_than_equal"}:
            message = f"'{field}' is below the allowed minimum."

        elif error_type in {"less_than", "less_than_equal"}:
            message = f"'{field}' exceeds the allowed maximum."

        elif error_type == "literal_error":
            message = f"'{field}' contains an unsupported value."

        else:
            message = f"'{field}' has an invalid value."

        issues.append(message)

    return create_error_response(
        code="INVALID_INPUT",
        message="One or more input fields failed validation.",
        action="Correct the following fields and call the tool again: "
        + " ".join(issues),
    )


def handle_google_api_error(exc: HttpError) -> str:
    """Convert Google Calendar HTTP errors into actionable messages."""

    status = getattr(exc.resp, "status", None)

    if status == 400:
        return create_error_response(
            code="INVALID_CALENDAR_REQUEST",
            message="Google Calendar rejected the request because its data is invalid.",
            action="Check the event dates, times, recurrence settings, and update fields.",
        )

    if status == 401:
        return create_error_response(
            code="AUTHENTICATION_REQUIRED",
            message="Google Calendar authentication is missing or expired.",
            action="Reconnect the Google account and refresh its OAuth credentials.",
        )

    if status == 403:
        # Google sometimes uses 403 for quota limits as well as permissions.
        try:
            content = json.loads(exc.content.decode("utf-8"))
            reasons = {
                item.get("reason")
                for item in content.get("error", {}).get("errors", [])
            }
        except (ValueError, AttributeError, TypeError):
            reasons = set()

        quota_reasons = {
            "quotaExceeded",
            "rateLimitExceeded",
            "userRateLimitExceeded",
        }

        if reasons.intersection(quota_reasons):
            return create_error_response(
                code="API_QUOTA_EXCEEDED",
                message="Google Calendar API quota or rate limit has been reached.",
                action="Wait before retrying. Reduce repeated requests if the problem continues.",
                retryable=True,
            )

        return create_error_response(
            code="INSUFFICIENT_PERMISSIONS",
            message="The connected Google account does not have permission for this operation.",
            action="Check the account's Calendar permissions and OAuth scopes.",
        )

    if status == 404:
        return create_error_response(
            code="EVENT_NOT_FOUND",
            message="The requested calendar event or calendar could not be found.",
            action="Verify the event ID and calendar ID using the event search or calendar list tool.",
        )

    if status == 409:
        return create_error_response(
            code="CALENDAR_CONFLICT",
            message="Google Calendar could not complete the operation because of a conflict.",
            action="Retrieve the latest event details and retry with the current event information.",
        )

    if status == 429:
        return create_error_response(
            code="API_RATE_LIMITED",
            message="Google Calendar is temporarily rate-limiting requests.",
            action="Wait before retrying the operation.",
            retryable=True,
        )

    if status and status >= 500:
        return create_error_response(
            code="CALENDAR_SERVICE_UNAVAILABLE",
            message="Google Calendar is temporarily unavailable.",
            action="Retry the operation after a short delay.",
            retryable=True,
        )

    return create_error_response(
        code="GOOGLE_API_ERROR",
        message="The Google Calendar API could not complete the requested operation.",
        action="Check Google Calendar availability and retry. If the problem continues, inspect server logs.",
    )


def handle_application_error(exc: CalendarError) -> str:
    """Convert application-specific errors into client responses."""

    code = getattr(exc, "code", "CALENDAR_ERROR")

    action_map = {
        "EVENT_NOT_FOUND":
            "Search for the event again and verify its event ID.",

        "EVENT_ALREADY_CANCELLED":
            "No deletion is necessary because the event is already cancelled.",

        "EVENT_CONFLICT":
            "Choose another time or obtain explicit confirmation to schedule despite the conflict.",

        "CONFIRMATION_REQUIRED":
            "Ask the user for explicit confirmation before retrying the deletion.",

        "AUTHENTICATION_REQUIRED":
            "Reconnect the Google account and refresh OAuth credentials.",

        "INSUFFICIENT_PERMISSIONS":
            "Check Google Calendar permissions and required OAuth scopes.",

        "API_QUOTA_EXCEEDED":
            "Wait before retrying. Reduce repeated API calls if the issue persists.",

        "CALENDAR_SERVICE_UNAVAILABLE":
            "Retry after a short delay.",

        "NETWORK_ERROR":
            "Check network connectivity and retry.",
    }

    return create_error_response(
        code=code,
        message=str(exc),
        action=action_map.get(
            code,
            "Correct the issue and call the tool again.",
        ),
        retryable=getattr(exc, "retryable", False),
    )


def handle_error(exc: Exception) -> str:
    """Classify an exception and return a safe client-facing response."""

    if isinstance(exc, ToolError):
        return str(exc)

    if isinstance(exc, ValidationError):
        return handle_validation_error(exc)

    if isinstance(exc, CalendarError):
        return handle_application_error(exc)

    if isinstance(exc, HttpError):
        return handle_google_api_error(exc)

    if isinstance(exc, ValueError):
        return create_error_response(
            code="INVALID_INPUT",
            message=str(exc),
            action="Correct the supplied values and call the tool again.",
        )

    if isinstance(exc, (RefreshError, GoogleAuthError)):
        return create_error_response(
            code="AUTHENTICATION_REQUIRED",
            message="Google account authentication failed.",
            action="Reconnect the Google account and check its OAuth credentials.",
        )

    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return create_error_response(
            code="NETWORK_ERROR",
            message="The server could not connect to Google Calendar.",
            action="Check network connectivity and retry.",
            retryable=True,
        )

    logger.exception("Unexpected error in Google Calendar MCP")

    return create_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred while processing the calendar request.",
        action="Retry once. If the problem continues, contact the server administrator with the tool name and approximate time of failure.",
    )


def handle_tool_errors(func):
    """Decorator for consistent error handling across MCP tools."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except Exception as exc:
            error_message = handle_error(exc)
            raise ToolError(error_message) from exc

    return wrapper