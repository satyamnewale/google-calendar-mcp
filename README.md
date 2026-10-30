# Google Calendar MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to interact with Google Calendar through structured tools for event management, calendar search, availability checking, and calendar summaries.

Built with Python, Google Calendar API, and FastMCP, this project connects an AI assistant to Google Calendar using a modular service-based architecture.

## ✨ Features

- **Event Creation** — Create timed, all-day, and multi-day calendar events.
- **Event Updates** — Modify existing event details.
- **Event Deletion** — Delete specific calendar events.
- **Event Retrieval** — Retrieve details of individual events.
- **Event Search** — Search calendar events using dates, date ranges, and event titles.
- **Similar Event Search** — Find events using approximate title matching.
- **Calendar Availability** — Check available time slots and identify scheduling conflicts.
- **Available Slot Suggestions** — Suggest suitable time slots based on calendar availability.
- **Recurring Events** — Create daily, weekly, monthly, and yearly recurring events with configurable intervals, weekdays, occurrence counts, and end dates.
- **Event Postponement** — Postpone existing calendar events.
- **Calendar Overview** — Retrieve daily, weekly, and monthly calendar summaries.
- **Google OAuth Authentication** — Authenticate users through Google OAuth 2.0.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation |
| Model Context Protocol (MCP) | Exposes Google Calendar functionality as tools |
| FastMCP | MCP server and tool registration |
| Google Calendar API | Calendar event and availability operations |
| Google OAuth 2.0 | User authentication and authorization |
| `uv` | Python project and dependency management |
| Pytest | Automated testing |

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
       +------------+-------------+
       |            |             |
       v            v             v
  Event Service  Event Search  Availability
       |            |          Service
       |            |             |
       +------------+-------------+
                    |
                    v
              Calendar Service
                    |
                    v
             Google Calendar API
                    |
                    v
              Google Account

       Supporting Components:
       - Authentication
       - Configuration
       - Date/Time Utilities
       - Recurrence Utilities
       - Input Validation
       - Calendar Summary
```

The MCP server exposes focused calendar tools. The AI assistant selects the appropriate tool based on the user's request, while the service layer handles event operations, availability checks, validation, and communication with the Google Calendar API.

## 🔧 Available MCP Tools

### 1. `create_calendar_event`

Create a calendar event.

Supports:
- Timed events
- All-day events
- Multi-day events
- Recurring events
- Event descriptions and locations
- Reminder configuration
- Availability conflict checking

Recurring event configuration supports frequency, interval, weekdays, occurrence count, and end date.

### 2. `edit_calendar_event`

Update the details of an existing calendar event.

### 3. `remove_calendar_event`

Delete a specific calendar event.

### 4. `get_calendar_event`

Retrieve the details of an individual calendar event.

### 5. `postpone_calendar_event`

Postpone an existing event to a different date or time.

### 6. `find_calendar_events`

Search calendar events using supported date and title conditions.

### 7. `find_similar_calendar_events`

Find events with similar titles using approximate matching.

### 8. `get_calendar_overview`

Retrieve a structured overview of calendar events for a requested period.

### 9. `check_calendar_availability`

Check whether a requested time interval is available and return detected conflicts.

### 10. `suggest_available_slots`

Suggest available time slots within a requested period.

### 11. `get_calendar_list`

Retrieve the available Google Calendars associated with the authenticated account.

## 📁 Project Structure

```text
calendar-mcp/
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
│
├── utils/
│   ├── __init__.py
│   ├── datetime_utils.py
│   ├── recurrence_utils.py
│   └── validators.py
│
├── credentials.json
├── token.json
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
| `calendar_summary.py` | Calendar summaries |
| `event_search.py` | Event search and approximate title matching |
| `event_service.py` | Event creation, updates, deletion, retrieval, and postponement |
| `tests/` | Automated test cases |
| `utils/` | Reusable helper functions |
| `datetime_utils.py` | Date parsing, timezone conversion, and date ranges |
| `recurrence_utils.py` | Recurrence rule construction and validation |
| `validators.py` | Input validation |
| `server.py` | MCP server and tool definitions |

`credentials.json` and `token.json` are local authentication files and should not be committed to a public repository.

## 🚀 Getting Started

### Prerequisites

- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)
- [Git](https://git-scm.com/)
- A Google account with Google Calendar
- A Google Cloud project with Google Calendar API enabled
- An OAuth client configured for the application

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/calendar-mcp.git
cd calendar-mcp
```

Replace `YOUR_USERNAME` with your GitHub username.

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
| `credentials.json` | Contains the OAuth client credentials downloaded from Google Cloud Console |
| `token.json` | Stores the authentication token generated after successful authorization |

### Authentication Flow

1. The MCP server starts.
2. The authentication module checks for an existing token.
3. If a valid token exists, it is reused.
4. Otherwise, the OAuth authorization flow is initiated.
5. After successful authorization, the token is generated and saved.
6. The authenticated credentials are used to access Google Calendar API.

For users running their own instance, their Google account may need to be added as a test user while the OAuth application is in testing mode.

## ▶️ Running the MCP Server

Run the server from the project root:

```bash
uv run fastmcp run server.py --transport stdio
```

The server uses STDIO transport, allowing an MCP client to launch the local process and communicate with it.

## 🔌 Codex Integration

OpenAI Codex can connect to external MCP servers and use their tools while working with a project.

### 1. Install Codex CLI

Follow the official installation instructions:

https://developers.openai.com/codex/cli/

On Windows, Codex can be installed using the official PowerShell installation instructions or through the supported npm installation method.

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

https://chatgpt.com/download/

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
- Protect local authentication files from unauthorized access.

If credentials are accidentally exposed, revoke or rotate them through Google Cloud Console.

## 🤝 Credits

This project and its documentation were written with AI assistance and reviewed by the repository owner.

**Built with Python, Google Calendar API, and Model Context Protocol (MCP).**