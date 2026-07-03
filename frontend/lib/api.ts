import type { AuditEvent, ExecutionResult, Role, ScriptDefinition } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_SAFEOPS_API ?? "http://localhost:8000";

export const demoScripts: ScriptDefinition[] = [
  {
    id: "restart-service",
    name: "Restart managed service",
    description:
      "Restarts an approved service after collecting a reason and downtime acknowledgement.",
    script_language: "bash",
    script_body: "echo Restarting $service_name",
    output_format: "json",
    allowed_roles: ["admin", "operator"],
    inputs: [
      {
        name: "service_name",
        type: "select",
        label: "Service",
        required: true,
        options: ["nginx", "apache", "mysql"],
        help_text: "Only approved services are available.",
      },
      { name: "reason", type: "text", label: "Reason for restart", required: true },
      {
        name: "confirm_downtime",
        type: "boolean",
        label: "I understand this may cause brief downtime.",
        required: true,
      },
    ],
    policy: {
      image: "alpine:latest",
      timeout_seconds: 45,
      memory_limit: "96m",
      cpu_quota: 50000,
      cpu_period: 100000,
      network: "none",
      allow_internet: false,
    },
    tags: ["incident-response", "linux", "approved"],
    approval_required: false,
  },
  {
    id: "clear-cache",
    name: "Clear application cache",
    description: "Flushes an application cache namespace without database access.",
    script_language: "bash",
    script_body: "echo Clearing $namespace",
    output_format: "text",
    allowed_roles: ["admin", "operator"],
    inputs: [
      {
        name: "namespace",
        type: "select",
        label: "Cache namespace",
        required: true,
        options: ["catalog", "checkout", "cms"],
      },
      { name: "ticket_id", type: "text", label: "Change ticket", required: true },
    ],
    policy: {
      image: "alpine:latest",
      timeout_seconds: 20,
      memory_limit: "64m",
      cpu_quota: 50000,
      cpu_period: 100000,
      network: "none",
      allow_internet: false,
    },
    tags: ["low-risk", "cache"],
    approval_required: false,
  },
  {
    id: "database-backup",
    name: "Create database backup",
    description: "Starts a constrained backup task for a selected database.",
    script_language: "bash",
    script_body: "echo Backing up $database",
    output_format: "text",
    allowed_roles: ["admin"],
    inputs: [
      {
        name: "database",
        type: "select",
        label: "Database",
        required: true,
        options: ["analytics", "billing", "identity"],
      },
      { name: "retention_days", type: "number", label: "Retention days", required: true, default: 7 },
    ],
    policy: {
      image: "alpine:latest",
      timeout_seconds: 300,
      memory_limit: "256m",
      cpu_quota: 50000,
      cpu_period: 100000,
      network: "restricted",
      allow_internet: false,
    },
    tags: ["admin-only", "backup"],
    approval_required: true,
  },
];

async function request<T>(path: string, role: Role, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      "x-safeops-role": role,
      "x-safeops-user": `${role}@safeops.local`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

export async function fetchScripts(): Promise<ScriptDefinition[]> {
  try {
    const response = await fetch(`${API_BASE}/api/scripts`, { cache: "no-store" });
    if (!response.ok) throw new Error("API unavailable");
    return response.json() as Promise<ScriptDefinition[]>;
  } catch {
    return demoScripts;
  }
}

export async function executeScript(
  scriptId: string,
  inputs: Record<string, unknown>,
  role: Role,
  mode: "preview" | "run",
): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/api/scripts/${scriptId}/${mode}`, role, {
    method: "POST",
    body: JSON.stringify({ inputs }),
  });
}

export async function fetchAudit(role: Role): Promise<AuditEvent[]> {
  return request<AuditEvent[]>("/api/audit", role);
}
