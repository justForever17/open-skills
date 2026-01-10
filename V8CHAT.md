# V8CHAT System Context (Universal Computer)

This service provides a secure execution environment (Docker Sandbox) for "Worker Agents". It follows the "Environment-as-a-Service" pattern.

## Architecture

- **Service**: FastAPI + MCP SDK (Port 8000)
- **Runtime**: Docker Container (`v8chat-sandbox`)
- **Protocol**: MCP over SSE

## Atomic Tools Exposed

1. `execute_command(command)`: Runs bash commands in the sandbox.
2. `manage_skills(action)`: Discovers skills by reading `SKILL.md`.
3. `read_file(path)` / `write_file(path, content)`: Filesystem access.

## Filesystem Map

| Sandbox Path | Host Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `/app/skills` | `apps/skill-runner/skills` | Skill Manuals & Scripts | Read-Only |
| `/share` | `apps/admin/public/jt` | User Workspace (Images, HTML) | Read-Write |

## How to add a new Skill

1. Create folder `skills/<category>/<skill-name>`.
2. Add `SKILL.md` (metadata & instructions).
3. Add `scripts/` (if needed).
4. Add `requirements.txt`.

## Development

- Run: `./venv/Scripts/python -m uvicorn main:mcp.sse_app --port 8000`
- Test: `./venv/Scripts/python test_sandbox.py`
