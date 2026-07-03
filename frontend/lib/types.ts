export type Role = "admin" | "operator" | "viewer";
export type InputType = "text" | "password" | "select" | "boolean" | "number";

export interface InputField {
  name: string;
  type: InputType;
  label: string;
  required: boolean;
  help_text?: string;
  options?: string[];
  default?: string | number | boolean;
  pattern?: string;
}

export interface SandboxPolicy {
  image: string;
  timeout_seconds: number;
  memory_limit: string;
  cpu_quota: number;
  cpu_period: number;
  network: "none" | "restricted" | "open";
  allow_internet: boolean;
}

export interface ScriptDefinition {
  id: string;
  name: string;
  description: string;
  script_language: "bash" | "python" | "powershell";
  script_body: string;
  output_format: "text" | "json";
  allowed_roles: Role[];
  inputs: InputField[];
  policy: SandboxPolicy;
  tags: string[];
  approval_required: boolean;
}

export interface ExecutionResult {
  run_id: string;
  script_id: string;
  status: "queued" | "running" | "success" | "failed" | "timeout" | "denied" | "dry_run";
  output: string;
  exit_code: number | null;
  started_at: string;
  finished_at: string | null;
  policy: SandboxPolicy;
  user: string;
  role: Role;
  redacted_inputs: Record<string, unknown>;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  user: string;
  role: Role;
  script_id: string;
  action: "preview" | "run";
  status: string;
  inputs: Record<string, unknown>;
  exit_code: number | null;
  output_excerpt: string;
}
