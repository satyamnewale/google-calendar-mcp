
import pytest

from fastmcp.exceptions import ToolError

from errors.error_handler import handle_tool_errors

@pytest.mark.unit
def test_successful_function_returns_result():

    @handle_tool_errors
    def sample_tool():
        return {"success": True}

    result = sample_tool()

    assert result == {"success": True}

@pytest.mark.unit
def test_value_error_is_converted_to_tool_error():

    @handle_tool_errors
    def sample_tool():
        raise ValueError("Invalid date")

    with pytest.raises(ToolError):
        sample_tool()

@pytest.mark.unit
def test_unexpected_error_is_converted_to_tool_error():

    @handle_tool_errors
    def sample_tool():
        raise RuntimeError("Internal failure")

    with pytest.raises(ToolError):
        sample_tool()

@pytest.mark.unit
def test_function_arguments_are_preserved():

    @handle_tool_errors
    def sample_tool(title, reminder_minutes=10):
        return {
            "title": title,
            "reminder_minutes": reminder_minutes,
        }

    result = sample_tool("Team Meeting", reminder_minutes=15)

    assert result["title"] == "Team Meeting"
    assert result["reminder_minutes"] == 15

@pytest.mark.unit
def test_function_return_list():

    @handle_tool_errors
    def sample_tool():
        return [{"id": "event_001"}]

    result = sample_tool()

    assert isinstance(result, list)
    assert result[0]["id"] == "event_001"
