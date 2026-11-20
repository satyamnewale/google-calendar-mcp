import json
import logging

from pydantic import ValidationError
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, GoogleAuthError
from fastmcp.exceptions import ToolError

from errors.exceptions import CalendarError

logger = logging.getLogger("google_calendar_mcp")


def create_error_response(
    code: str,
    message: str,
    action: str,
    retryable: bool = False,
) -> str:
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
        action=(
            "Correct the following fields and call the tool again: "
            + " ".join(issues)
        ),
    )


def handle_google_api_error(exc: HttpError) -> str:
    status = getattr(exc.resp, "status", None)

    if status == 400:
        return create_error_response(
            "INVALID_CALENDAR_REQUEST",
            "Google Calendar rejected the request because its data is invalid.",
            "Check event dates, times, recurrence settings, and update fields.",
        )

    if status == 401:
        return create_error_response(
            "AUTHENTICATION_REQUIRED",
            "Google Calendar authentication is missing or expired.",
            "Reconnect the Google account and refresh its OAuth credentials.",
        )

    if status == 403:
        try:
            content = json.loads(exc.content.decode("utf-8"))
            reasons = {
                item.get("reason")
                for item in content.get("error", {}).get("errors", [])
            }
        except (ValueError, AttributeError, TypeError):
            reasons = set()

        if reasons.intersection({
            "quotaExceeded",
            "rateLimitExceeded",
            "userRateLimitExceeded",
        }):
            return create_error_response(
                "API_QUOTA_EXCEEDED",
                "Google Calendar API quota or rate limit has been reached.",
                "Wait before retrying and reduce repeated requests.",
                retryable=True,
            )

        return create_error_response(
            "INSUFFICIENT_PERMISSIONS",
            "The connected Google account does not have permission.",
            "Check Calendar permissions and OAuth scopes.",
        )

    if status == 404:
        return create_error_response(
            "EVENT_NOT_FOUND",
            "The requested calendar event or calendar could not be found.",
            "Verify the event ID and calendar ID.",
        )

    if status in (409, 412):
        return create_error_response(
            "EVENT_MODIFIED_CONCURRENTLY",
            "The event changed during the requested operation.",
            "Retrieve the latest event and reconcile the requested changes.",
        )

    if status == 429:
        return create_error_response(
            "API_RATE_LIMITED",
            "Google Calendar is temporarily rate-limiting requests.",
            "Wait before retrying.",
            retryable=True,
        )

    if status and status >= 500:
        return create_error_response(
            "CALENDAR_SERVICE_UNAVAILABLE",
            "Google Calendar is temporarily unavailable.",
            "Retry after a short delay.",
            retryable=True,
        )

    return create_error_response(
        "GOOGLE_API_ERROR",
        "Google Calendar could not complete the operation.",
        "Check Calendar availability and inspect server logs.",
    )


def handle_error(exc: Exception) -> str:
    if isinstance(exc, ToolError):
        return str(exc)

    if isinstance(exc, ValidationError):
        return handle_validation_error(exc)

    if isinstance(exc, CalendarError):
        return create_error_response(
            code=getattr(exc, "code", "CALENDAR_ERROR"),
            message=str(exc),
            action="Correct the issue and call the tool again.",
            retryable=getattr(exc, "retryable", False),
        )

    if isinstance(exc, HttpError):
        return handle_google_api_error(exc)

    if isinstance(exc, ValueError):
        return create_error_response(
            "INVALID_INPUT",
            str(exc),
            "Correct the supplied values and call the tool again.",
        )

    if isinstance(exc, (RefreshError, GoogleAuthError)):
        return create_error_response(
            "AUTHENTICATION_REQUIRED",
            "Google account authentication failed.",
            "Reconnect the Google account and check OAuth credentials.",
        )

    if isinstance(exc, FileNotFoundError):
        logger.error("Required OAuth configuration file is missing.")
        return create_error_response(
            "OAUTH_CONFIGURATION_MISSING",
            "The Google OAuth client credentials file is missing.",
            "Configure OAuth client credentials for this server instance.",
        )

    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return create_error_response(
            "NETWORK_ERROR",
            "The server could not connect to Google Calendar.",
            "Check network connectivity and retry.",
            retryable=True,
        )

    logger.exception("Unexpected Google Calendar MCP error")

    return create_error_response(
        "INTERNAL_SERVER_ERROR",
        "An unexpected error occurred.",
        "Retry once. Contact the server administrator if the issue continues.",
    )