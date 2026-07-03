# SafeOps Studio

SafeOps Studio turns privileged operational scripts into secure, role-based web workflows.
Admins define one Bash/Python/PowerShell-style runbook schema; operators get a generated form,
dry-run preview, sandboxed execution, and immutable audit evidence.

## What is upgraded

- **Security-first execution**: Docker sandbox settings for network isolation, memory caps, CPU quotas,
  hard timeouts, per-run labels, and forced container cleanup.
- **Generated operations UI**: Script definitions drive forms, validation, policy cards, output viewers,
  and RBAC states without writing custom HTML per runbook.
- **Role-aware workflows**: Admin, operator, and viewer roles demonstrate execution permissions and
  audit visibility.
- **Audit trail**: SQLite-backed append-only event records capture actor, role, script, inputs,
  status, output excerpt, and exit code.
- **Dry-run preview**: Users can inspect the exact command and sandbox policy before execution.

## Repository layout

```text
backend/   FastAPI API, script catalog, sandbox runner, audit store, tests
frontend/  Next.js + Tailwind console with dynamic forms and audit viewer
```

## Run locally

```bash
docker compose up
```

Open `http://localhost:3000`.

The backend defaults to `SAFEOPS_EXECUTION_MODE=simulate` so demos work without a Docker daemon inside
the runtime environment. Set `SAFEOPS_EXECUTION_MODE=docker` for real Docker-backed script execution.

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
pytest
```

Useful endpoints:

- `GET /api/scripts`
- `POST /api/scripts/{script_id}/preview`
- `POST /api/scripts/{script_id}/run`
- `GET /api/audit`

Demo identity is supplied through headers:

- `x-safeops-role: admin | operator | viewer`
- `x-safeops-user: name@example.com`

## Frontend

```bash
cd frontend
npm install
npm run dev
npm run build
```
