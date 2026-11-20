
import json

import pytest
from fastmcp.exceptions import ToolError

from errors.error_handler import (
    create_error_response,
    handle_error,
)


@pytest.mark.unit
def test_create_error_response():
    result = create_error_response(
        code="INVALID_INPUT",
        message="Invalid date",
        action="Correct the supplied values.",
    )

    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["code"] == "INVALID_INPUT"
    assert parsed["error"]["message"] == "Invalid date"
    assert parsed["error"]["action"] == "Correct the supplied values."
    assert parsed["error"]["retryable"] is False


@pytest.mark.unit
def test_create_error_response_retryable():
    result = create_error_response(
        code="NETWORK_ERROR",
        message="Connection failed",
        action="Retry later.",
        retryable=True,
    )

    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["retryable"] is True


@pytest.mark.unit
def test_value_error_is_converted_to_error_response():
    exc = ValueError("Invalid date")

    result = handle_error(exc)
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["code"] == "INVALID_INPUT"
    assert parsed["error"]["message"] == "Invalid date"


@pytest.mark.unit
def test_unexpected_error_is_converted_to_internal_error():
    exc = RuntimeError("Internal failure")

    result = handle_error(exc)
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["code"] == "INTERNAL_SERVER_ERROR"


@pytest.mark.unit
def test_tool_error_is_preserved():
    exc = ToolError("Tool execution failed")

    result = handle_error(exc)

    assert result == str(exc)


@pytest.mark.unit
def test_file_not_found_error():
    exc = FileNotFoundError("credentials.json")

    result = handle_error(exc)
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["code"] == "OAUTH_CONFIGURATION_MISSING"


@pytest.mark.unit
def test_connection_error_is_retryable():
    exc = ConnectionError("Network unavailable")

    result = handle_error(exc)
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["code"] == "NETWORK_ERROR"
    assert parsed["error"]["retryable"] is True


@pytest.mark.unit
def test_timeout_error_is_retryable():
    exc = TimeoutError("Request timed out")

    result = handle_error(exc)
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert parsed["error"]["code"] == "NETWORK_ERROR"
    assert parsed["error"]["retryable"] is True
