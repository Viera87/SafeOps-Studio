from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from string import Template
from typing import Any
from uuid import uuid4

import docker

from models import ExecutionResult, InputType, Role, ScriptDefinition


class ValidationError(ValueError):
    pass


def validate_inputs(script: ScriptDefinition, inputs: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    fields = {field.name: field for field in script.inputs}

    for field in script.inputs:
        raw_value = inputs.get(field.name, field.default)
        if field.required and (raw_value is None or raw_value == "" or raw_value is False):
            raise ValidationError(f"{field.label} is required")

        if raw_value is None:
            continue

        if field.type == InputType.select:
            if raw_value not in (field.options or []):
                raise ValidationError(f"{field.label} must be one of: {', '.join(field.options or [])}")
            cleaned[field.name] = raw_value
        elif field.type == InputType.boolean:
            cleaned[field.name] = bool(raw_value)
        elif field.type == InputType.number:
            try:
                cleaned[field.name] = int(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"{field.label} must be a number") from exc
        else:
            value = str(raw_value).strip()
            if field.pattern and not re.match(field.pattern, value):
                raise ValidationError(f"{field.label} has an invalid format")
            cleaned[field.name] = value

    unknown = sorted(set(inputs) - set(fields))
    if unknown:
        raise ValidationError(f"Unknown input fields: {', '.join(unknown)}")

    return cleaned


def redact_inputs(script: ScriptDefinition, inputs: dict[str, Any]) -> dict[str, Any]:
    password_fields = {field.name for field in script.inputs if field.type == InputType.password}
    return {key: ("[REDACTED]" if key in password_fields else value) for key, value in inputs.items()}


def preview_command(script: ScriptDefinition, inputs: dict[str, Any]) -> str:
    exports = "\n".join(f"export {key}={json.dumps(str(value))}" for key, value in inputs.items())
    return f"{exports}\n{script.script_body}".strip()


def user_can_run(script: ScriptDefinition, role: Role) -> bool:
    return role in script.allowed_roles


class SandboxRunner:
    def __init__(self, mode: str | None = None):
        self.mode = mode or os.getenv("SAFEOPS_EXECUTION_MODE", "simulate")

    def dry_run(self, script: ScriptDefinition, inputs: dict[str, Any], user: str, role: Role) -> ExecutionResult:
        now = datetime.now(timezone.utc)
        output = "\n".join(
            [
                "Dry run preview",
                f"Script: {script.name}",
                f"Image: {script.policy.image}",
                f"Network: {script.policy.network}",
                f"Timeout: {script.policy.timeout_seconds}s",
                "Command:",
                preview_command(script, inputs),
            ]
        )
        return ExecutionResult(
            run_id=str(uuid4()),
            script_id=script.id,
            status="dry_run",
            output=output,
            exit_code=None,
            started_at=now,
            finished_at=now,
            policy=script.policy,
            user=user,
            role=role,
            redacted_inputs=redact_inputs(script, inputs),
        )

    def run(self, script: ScriptDefinition, inputs: dict[str, Any], user: str, role: Role) -> ExecutionResult:
        if self.mode == "docker":
            return self._run_docker(script, inputs, user, role)
        return self._run_simulated(script, inputs, user, role)

    def _run_simulated(
        self, script: ScriptDefinition, inputs: dict[str, Any], user: str, role: Role
    ) -> ExecutionResult:
        now = datetime.now(timezone.utc)
        rendered = Template(script.script_body).safe_substitute(inputs)
        output = "\n".join(
            [
                "SafeOps simulated sandbox",
                f"Applied policy: network={script.policy.network}, mem={script.policy.memory_limit}",
                rendered,
            ]
        )
        time.sleep(0.1)
        return ExecutionResult(
            run_id=str(uuid4()),
            script_id=script.id,
            status="success",
            output=output,
            exit_code=0,
            started_at=now,
            finished_at=datetime.now(timezone.utc),
            policy=script.policy,
            user=user,
            role=role,
            redacted_inputs=redact_inputs(script, inputs),
        )

    def _run_docker(self, script: ScriptDefinition, inputs: dict[str, Any], user: str, role: Role) -> ExecutionResult:
        started = datetime.now(timezone.utc)
        client = docker.from_env()
        command = preview_command(script, inputs)
        network_mode = "none" if not script.policy.allow_internet else "bridge"
        container = None
        try:
            container = client.containers.run(
                image=script.policy.image,
                command=["sh", "-c", command],
                detach=True,
                network_mode=network_mode,
                mem_limit=script.policy.memory_limit,
                cpu_period=script.policy.cpu_period,
                cpu_quota=script.policy.cpu_quota,
                labels={"safeops.script_id": script.id, "safeops.user": user},
            )
            result = container.wait(timeout=script.policy.timeout_seconds)
            output = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            exit_code = int(result.get("StatusCode", 1))
            status = "success" if exit_code == 0 else "failed"
        except Exception as exc:
            if container:
                container.stop(timeout=1)
            output = f"Sandbox execution failed: {exc}"
            exit_code = None
            status = "timeout" if "Read timed out" in str(exc) else "failed"
        finally:
            if container:
                container.remove(force=True)

        return ExecutionResult(
            run_id=str(uuid4()),
            script_id=script.id,
            status=status,
            output=output,
            exit_code=exit_code,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            policy=script.policy,
            user=user,
            role=role,
            redacted_inputs=redact_inputs(script, inputs),
        )
