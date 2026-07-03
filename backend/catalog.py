from __future__ import annotations

from models import InputField, InputType, Role, SandboxPolicy, ScriptDefinition


SCRIPT_CATALOG: dict[str, ScriptDefinition] = {
    "restart-service": ScriptDefinition(
        id="restart-service",
        name="Restart managed service",
        description=(
            "Restarts an approved service after collecting a reason and downtime "
            "acknowledgement. Intended for incident response runbooks."
        ),
        script_body="""
echo "Preparing restart for $service_name"
echo "Reason: $reason"
echo "Stopping $service_name..."
sleep 1
echo "Starting $service_name..."
echo '{"service":"'$service_name'","status":"healthy","downtime_seconds":18}'
""".strip(),
        output_format="json",
        allowed_roles=[Role.admin, Role.operator],
        inputs=[
            InputField(
                name="service_name",
                type=InputType.select,
                label="Service",
                required=True,
                options=["nginx", "apache", "mysql"],
                help_text="Only allowlisted services are exposed to operators.",
            ),
            InputField(
                name="reason",
                type=InputType.text,
                label="Reason for restart",
                required=True,
                help_text="Stored in the audit trail for post-incident review.",
            ),
            InputField(
                name="confirm_downtime",
                type=InputType.boolean,
                label="I understand this may cause brief downtime.",
                required=True,
            ),
        ],
        policy=SandboxPolicy(timeout_seconds=45, memory_limit="96m", network="none"),
        tags=["incident-response", "linux", "approved"],
    ),
    "clear-cache": ScriptDefinition(
        id="clear-cache",
        name="Clear application cache",
        description="Flushes an application cache namespace without database access.",
        script_body="""
echo "Clearing cache namespace: $namespace"
echo "Requested by ticket: $ticket_id"
echo "Cache clear completed"
""".strip(),
        allowed_roles=[Role.admin, Role.operator],
        inputs=[
            InputField(
                name="namespace",
                type=InputType.select,
                label="Cache namespace",
                required=True,
                options=["catalog", "checkout", "cms"],
            ),
            InputField(
                name="ticket_id",
                type=InputType.text,
                label="Change ticket",
                required=True,
                pattern=r"^(INC|CHG)-[0-9]{4,}$",
                help_text="Example: CHG-1042",
            ),
        ],
        policy=SandboxPolicy(timeout_seconds=20, memory_limit="64m", network="none"),
        tags=["low-risk", "cache"],
    ),
    "database-backup": ScriptDefinition(
        id="database-backup",
        name="Create database backup",
        description="Starts a constrained backup task for a selected database.",
        script_body="""
echo "Creating backup for $database"
echo "Retention: $retention_days days"
echo "Backup manifest written to immutable storage"
""".strip(),
        allowed_roles=[Role.admin],
        inputs=[
            InputField(
                name="database",
                type=InputType.select,
                label="Database",
                required=True,
                options=["analytics", "billing", "identity"],
            ),
            InputField(
                name="retention_days",
                type=InputType.number,
                label="Retention days",
                required=True,
                default=7,
            ),
        ],
        policy=SandboxPolicy(timeout_seconds=300, memory_limit="256m", network="restricted"),
        tags=["admin-only", "backup"],
        approval_required=True,
    ),
}


def list_scripts() -> list[ScriptDefinition]:
    return list(SCRIPT_CATALOG.values())


def get_script(script_id: str) -> ScriptDefinition | None:
    return SCRIPT_CATALOG.get(script_id)
