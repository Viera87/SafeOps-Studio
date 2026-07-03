from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from audit import list_events, record_event
from catalog import get_script, list_scripts
from models import AuditEvent, ExecutionResult, Role, RunRequest, ScriptDefinition
from sandbox import SandboxRunner, ValidationError, user_can_run, validate_inputs

app = FastAPI(title="SafeOps Studio API", version="0.1.0")
runner = SandboxRunner()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CurrentUser:
    def __init__(self, user_id: str, role: Role):
        self.user_id = user_id
        self.role = role


def current_user(
    x_safeops_user: str = Header(default="demo.operator@safeops.local"),
    x_safeops_role: Role = Header(default=Role.operator),
) -> CurrentUser:
    return CurrentUser(user_id=x_safeops_user, role=x_safeops_role)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/scripts", response_model=list[ScriptDefinition])
async def scripts() -> list[ScriptDefinition]:
    return list_scripts()


@app.get("/api/scripts/{script_id}", response_model=ScriptDefinition)
async def script_detail(script_id: str) -> ScriptDefinition:
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@app.post("/api/scripts/{script_id}/preview", response_model=ExecutionResult)
async def preview_script(
    script_id: str, request: RunRequest, user: CurrentUser = Depends(current_user)
) -> ExecutionResult:
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if user.role == Role.viewer:
        raise HTTPException(status_code=403, detail="Viewers cannot preview executable scripts")

    try:
        inputs = validate_inputs(script, request.inputs)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = runner.dry_run(script, inputs, user.user_id, user.role)
    record_event(
        user=user.user_id,
        role=user.role,
        script_id=script.id,
        action="preview",
        status=result.status,
        inputs=result.redacted_inputs,
        output=result.output,
    )
    return result


@app.post("/api/scripts/{script_id}/run", response_model=ExecutionResult)
async def run_script(script_id: str, request: RunRequest, user: CurrentUser = Depends(current_user)) -> ExecutionResult:
    script = get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    if not user_can_run(script, user.role):
        record_event(
            user=user.user_id,
            role=user.role,
            script_id=script.id,
            action="run",
            status="denied",
            inputs=request.inputs,
            output="RBAC denied execution",
        )
        raise HTTPException(status_code=403, detail=f"{user.role.value} cannot run {script.id}")

    try:
        inputs = validate_inputs(script, request.inputs)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = runner.run(script, inputs, user.user_id, user.role)
    record_event(
        user=user.user_id,
        role=user.role,
        script_id=script.id,
        action="run",
        status=result.status,
        inputs=result.redacted_inputs,
        exit_code=result.exit_code,
        output=result.output,
    )
    return result


@app.get("/api/audit", response_model=list[AuditEvent])
async def audit_events(user: CurrentUser = Depends(current_user)) -> list[AuditEvent]:
    if user.role not in [Role.admin, Role.viewer]:
        raise HTTPException(status_code=403, detail="Only admins and viewers can inspect audit trails")
    return list_events()
