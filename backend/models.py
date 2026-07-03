from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Role(str, Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class InputType(str, Enum):
    text = "text"
    password = "password"
    select = "select"
    boolean = "boolean"
    number = "number"


class InputField(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    type: InputType
    label: str
    required: bool = False
    help_text: str | None = None
    options: list[str] | None = None
    default: Any = None
    pattern: str | None = None

    @field_validator("options")
    @classmethod
    def options_are_unique(cls, value: list[str] | None) -> list[str] | None:
        if value and len(value) != len(set(value)):
            raise ValueError("select options must be unique")
        return value


class SandboxPolicy(BaseModel):
    image: str = "alpine:latest"
    timeout_seconds: int = Field(default=30, ge=1, le=900)
    memory_limit: str = "128m"
    cpu_quota: int = Field(default=50000, ge=10000, le=100000)
    cpu_period: int = 100000
    network: Literal["none", "restricted", "open"] = "none"
    allow_internet: bool = False


class ScriptDefinition(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    description: str
    script_language: Literal["bash", "python", "powershell"] = "bash"
    script_body: str
    output_format: Literal["text", "json"] = "text"
    allowed_roles: list[Role] = Field(default_factory=lambda: [Role.admin, Role.operator])
    inputs: list[InputField]
    policy: SandboxPolicy = Field(default_factory=SandboxPolicy)
    tags: list[str] = Field(default_factory=list)
    approval_required: bool = False


class RunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class ExecutionResult(BaseModel):
    run_id: str
    script_id: str
    status: Literal["queued", "running", "success", "failed", "timeout", "denied", "dry_run"]
    output: str
    exit_code: int | None = None
    started_at: datetime
    finished_at: datetime | None = None
    policy: SandboxPolicy
    user: str
    role: Role
    redacted_inputs: dict[str, Any]


class AuditEvent(BaseModel):
    id: str
    timestamp: datetime
    user: str
    role: Role
    script_id: str
    action: Literal["preview", "run"]
    status: str
    inputs: dict[str, Any]
    exit_code: int | None = None
    output_excerpt: str = ""
