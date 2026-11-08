# Google Calendar MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to interact with Google Calendar through structured tools for event management, calendar search, availability checking, and calendar summaries.

Built with Python, Google Calendar API, and FastMCP, this project connects AI assistants to Google Calendar using a modular, service-based architecture.

## ✨ Features

- **Event Creation** — Create timed, all-day, and multi-day calendar events.
- **Event Updates** — Modify existing event details.
- **Event Deletion** — Delete specific calendar events with explicit confirmation.
- **Event Retrieval** — Retrieve details of individual calendar events.
- **Event Search** — Search calendar events using dates, date ranges, and event titles.
- **Similar Event Search** — Find events using approximate title matching.
- **Calendar Availability** — Check available time slots and identify scheduling conflicts.
- **Available Slot Suggestions** — Suggest suitable time slots based on calendar availability.
- **Recurring Events** — Create daily, weekly, monthly, and yearly recurring events with configurable intervals and weekdays.
- **Event Postponement** — Reschedule existing calendar events.
- **Calendar Overview** — Retrieve daily, weekly, and monthly calendar summaries.
- **Google OAuth Authentication** — Authenticate users through Google OAuth 2.0.
- **Automated Testing** — Test utilities, services, integration flows, and MCP tools using Pytest.
- **Continuous Integration** — Run automated tests through GitHub Actions.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.13 | Core implementation |
| Model Context Protocol (MCP) | Exposes Google Calendar functionality as tools |
| FastMCP | MCP server and tool registration |
| Google Calendar API | Calendar event and availability operations |
| Google OAuth 2.0 | User authentication and authorization |
| Pydantic | Input validation and schema enforcement |
| `uv` | Python project and dependency management |
| Pytest | Automated testing |
| GitHub Actions | Continuous integration |

## 🧠 Architecture

```text
                 AI Assistant / MCP Client
                           |
                           | MCP tool calls
                           v
                     FastMCP Server
                       server.py
                           |
                           v
                       MCP Tools
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
       Event Service   Event Search   Availability
            |              |           Service
            |              |              |
            +--------------+--------------+
                           |
                           v
                     Calendar Service
                           |
                           v
                   Google Calendar API
                           |
                           v
                     Google Account


                  Supporting Components
                  ---------------------
                  Authentication
                  Configuration
                  Date/Time Utilities
                  Recurrence Utilities
                  Input Validation
                  Calendar Summary
                  Error Handling
```

The MCP server exposes focused calendar tools. The AI assistant selects the appropriate tool based on the user's request, while the service layer handles event operations, availability checks, validation, and communication with the Google Calendar API.

## 🔧 Available MCP Tools

The server currently exposes 11 MCP tools.

| No. | Tool | Description |
|---|---|---|
| 1 | `create_calendar_event` | Create timed, all-day, multi-day, or recurring events. Supports descriptions, locations, reminders, and availability conflict checking. |
| 2 | `edit_calendar_event` | Update details of an existing calendar event. |
| 3 | `remove_calendar_event` | Delete an event after explicit confirmation. |
| 4 | `get_calendar_event` | Retrieve details of an individual calendar event. |
| 5 | `postpone_calendar_event` | Reschedule an existing event to a different date or time. |
| 6 | `find_calendar_events` | Search calendar events using date ranges and optional title filtering. |
| 7 | `find_similar_calendar_events` | Find events with similar titles using approximate matching. |
| 8 | `get_calendar_overview` | Retrieve daily, weekly, and monthly calendar summaries. |
| 9 | `check_calendar_availability` | Check availability and identify scheduling conflicts. |
| 10 | `suggest_available_slots` | Suggest available time slots within a requested period. |
| 11 | `get_calendar_list` | Retrieve calendars associated with the authenticated Google account. |

### Event Creation and Recurrence

The `create_calendar_event` tool supports:

- Timed events.
- All-day events.
- Multi-day events.
- Recurring events.
- Event descriptions and locations.
- Reminder configuration.
- Availability conflict checking.

Recurring event configuration supports frequency, interval, and weekdays.

### Event Deletion and Confirmation

Deleting an event requires explicit confirmation. The server validates the confirmation before proceeding with the deletion operation.

## 📁 Project Structure

```text
google-calendar-mcp/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── auth/
│   └── google_auth.py
│
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── services/
│   ├── __init__.py
│   ├── availability_service.py
│   ├── calendar_service.py
│   ├── calendar_summary.py
│   ├── event_search.py
│   └── event_service.py
│
├── tests/
│   ├── conftest.py
│   │
│   ├── unit/
│   │   ├── test_datetime_utils.py
│   │   ├── test_recurrence_utils.py
│   │   ├── test_validators.py
│   │   ├── test_event_schema.py
│   │   └── test_error_handler.py
│   │
│   ├── integration/
│   │   ├── test_create_event_flow.py
│   │   ├── test_update_event_flow.py
│   │   ├── test_delete_event_flow.py
│   │   ├── test_postpone_event_flow.py
│   │   └── test_scheduling_flow.py
│   │
│   ├── services/
│   │   ├── test_event_service.py
│   │   ├── test_availability_service.py
│   │   ├── test_event_search.py
│   │   ├── test_calendar_summary.py
│   │   └── test_calendar_service.py
│   │
│   └── test_server_tools.py
│
├── utils/
│   ├── __init__.py
│   ├── datetime_utils.py
│   ├── recurrence_utils.py
│   ├── validators.py
│   └── error_handler.py
│
├── credentials.json        # Local OAuth credentials (not committed)
├── token.json              # Generated OAuth token (not committed)
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
├── server.py
└── README.md
```

### Folder Responsibilities

| Folder / File | Responsibility |
|---|---|
| `auth/` | Google OAuth authentication |
| `config/` | Application configuration and timezone settings |
| `services/` | Calendar operations and business logic |
| `availability_service.py` | Availability checking and free-slot suggestions |
| `calendar_service.py` | Google Calendar API operations |
| `calendar_summary.py` | Daily, weekly, and monthly summaries |
| `event_search.py` | Event search and approximate title matching |
| `event_service.py` | Event creation, updates, deletion, retrieval, and postponement |
| `tests/` | Automated test cases |
| `tests/conftest.py` | Shared test fixtures |
| `tests/unit/` | Unit tests for utilities, schemas, validators, and error handling |
| `tests/services/` | Service-layer tests |
| `tests/integration/` | Event and scheduling workflow tests |
| `test_server_tools.py` | MCP tool behaviour and validation tests |
| `utils/` | Reusable helper functions |
| `server.py` | MCP server and tool definitions |
| `.github/workflows/` | GitHub Actions CI configuration |

## 🚀 Getting Started

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- [Git](https://git-scm.com/)
- A Google account with Google Calendar
- A Google Cloud project with Google Calendar API enabled
- An OAuth client configured for the application

### 1. Clone the Repository

```bash
git clone https://github.com/satyamnewale/google-calendar-mcp.git

cd google-calendar-mcp
```

### 2. Create the Virtual Environment

```bash
uv venv
```

Activate it in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
uv sync
```

This installs the project dependencies defined in `pyproject.toml` and `uv.lock`.

## ☁️ Google Cloud Setup

The project requires Google Calendar API access through OAuth 2.0.

### 1. Create a Google Cloud Project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing project.
3. Open **APIs & Services**.
4. Navigate to **Library**.
5. Search for **Google Calendar API**.
6. Enable the API.

### 2. Configure OAuth Consent Screen

1. Open Google Auth Platform.
2. Configure the application information.
3. Select the appropriate audience.
4. Configure the required OAuth permissions.
5. Add test users if the application is in testing mode.

### 3. Create OAuth Credentials

1. Navigate to the OAuth client configuration.
2. Create an OAuth client suitable for the authentication flow implemented by the project.
3. Download the client credentials JSON file.
4. Save it in the project root as `credentials.json`.

## 🔐 Google OAuth Authentication

The project uses two files for Google authentication:

| File | Purpose |
|---|---|
| `credentials.json` | Contains OAuth client credentials downloaded from Google Cloud Console |
| `token.json` | Stores the authentication token generated after successful authorization |

### Authentication Flow

1. The MCP server starts.
2. The authentication module checks for an existing token.
3. If a valid token exists, it is reused.
4. Otherwise, the OAuth authorization flow is initiated.
5. After successful authorization, the token is generated and saved.
6. The authenticated credentials are used to access the Google Calendar API.

For users running their own instance, their Google account may need to be added as a test user while the OAuth application is in testing mode.

Each user should configure their own Google Cloud OAuth credentials.

## ▶️ Running the MCP Server

Run the server from the project root:

```bash
uv run fastmcp run server.py --transport stdio
```

The server uses **STDIO transport**, allowing an MCP client to launch the local process and communicate with it.

## 🧪 Testing

The project uses Pytest for automated testing across different layers.

### Test Categories

| Category | Purpose |
|---|---|
| Unit tests | Test individual utilities, validators, schemas, and error handlers |
| Service tests | Test calendar services, event operations, searching, summaries, and availability |
| Integration tests | Test complete event-management and scheduling workflows |
| Server tool tests | Test MCP tool registration, input validation, service calls, and tool behaviour |

### Run All Tests

```powershell
uv run python -m pytest
```

### Run Tests by Category

```powershell
# Unit tests
uv run python -m pytest -m unit

# Service tests
uv run python -m pytest -m service

# Integration tests
uv run python -m pytest -m integration
```

### Run a Specific Test File

```powershell
uv run python -m pytest tests/services/test_event_service.py -v
```

### Run with Detailed Output

```powershell
uv run python -m pytest -v
```

The project uses shared fixtures and mocked Google Calendar API responses to test service and tool behaviour without requiring real calendar operations for every test.

Pytest configuration and test markers are maintained in `pyproject.toml`.

## ⚙️ Continuous Integration — GitHub Actions

GitHub Actions is used to automate project testing.

The CI workflow is located at:

```text
.github/workflows/ci.yml
```

### CI Workflow

The workflow performs the following steps:

1. Checks out the repository.
2. Sets up Python 3.13.
3. Installs `uv`.
4. Installs dependencies using the committed lockfile.
5. Runs the Pytest test suite.

### Workflow Triggers

The CI workflow runs on:

- Pushes to `main`.
- Pushes to `develop`.
- Pull requests targeting `main` or `develop`.
- Manual workflow execution through GitHub Actions.

A failed test causes the workflow to fail, making it easier to identify regressions before merging changes.

## 🔌 Codex Integration

OpenAI Codex can connect to external MCP servers and use their tools while working with a project.

### 1. Install Codex CLI

Follow the official installation instructions:

[Codex CLI Installation](https://developers.openai.com/codex/cli/)

Verify the installation:

```bash
codex --version
```

### 2. Add the Calendar MCP Server

Register the local MCP server using:

```powershell
codex mcp add calendar_mcp -- "PATH_TO_UV_EXE" run --directory "PATH_TO_CALENDAR_MCP" fastmcp run server.py --transport stdio
```

Replace:

- `PATH_TO_UV_EXE` with the absolute path to the `uv.exe` executable.
- `PATH_TO_CALENDAR_MCP` with the absolute path to the Calendar MCP project directory.

### 3. Verify MCP Connection

```bash
codex mcp list
```

The registered Calendar MCP server should appear in the list.

Start Codex from the project directory:

```bash
codex
```

Once connected, Codex can discover and invoke the available Calendar MCP tools.

## 💻 ChatGPT for Windows

ChatGPT for Windows can be used alongside Codex during development.

Download the application:

[ChatGPT for Windows](https://chatgpt.com/download/)

ChatGPT can assist with:

- Understanding project architecture.
- Explaining Python and FastMCP functions.
- Reviewing implementation and code structure.
- Debugging errors.
- Understanding Google Calendar API operations.
- Improving documentation.
- Planning new features.

**Note:** Installing the ChatGPT Windows application does not automatically connect it to the local Calendar MCP server. The MCP connection described above is configured through Codex.

## 🔒 Security

Security is an important part of this project.

- OAuth credentials and tokens must remain outside version control.
- Do not publish `credentials.json` or `token.json`.
- Each user should configure their own Google Cloud OAuth credentials.
- Use only the required OAuth permissions.
- Validate event inputs before performing calendar operations.
- Require explicit confirmation before destructive operations.
- Protect local authentication files from unauthorized access.

If credentials are accidentally exposed, revoke or rotate them through Google Cloud Console.

## 🤝 Credits

This project and its documentation were written with AI assistance and reviewed by the repository owner.

Built with Python, Google Calendar API, and Model Context Protocol (MCP).