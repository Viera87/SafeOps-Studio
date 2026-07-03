"use client";

import {
  Activity,
  CheckCircle2,
  FileText,
  Lock,
  Play,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
} from "lucide-react";
import { useMemo, useState } from "react";

import { executeScript, fetchAudit } from "@/lib/api";
import type { AuditEvent, ExecutionResult, InputField, Role, ScriptDefinition } from "@/lib/types";

const roles: Role[] = ["admin", "operator", "viewer"];

function initialInputs(script: ScriptDefinition): Record<string, unknown> {
  return Object.fromEntries(
    script.inputs.map((field) => [
      field.name,
      field.default ?? (field.type === "boolean" ? false : field.type === "number" ? 1 : ""),
    ]),
  );
}

function roleBadge(role: Role) {
  if (role === "admin") return "bg-emerald-400/15 text-emerald-200 ring-emerald-300/30";
  if (role === "operator") return "bg-blue-400/15 text-blue-200 ring-blue-300/30";
  return "bg-slate-400/15 text-slate-200 ring-slate-300/30";
}

function Field({
  field,
  value,
  onChange,
}: {
  field: InputField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const base =
    "mt-2 w-full rounded-2xl border border-slate-700/80 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-cyan-300 focus:ring-4 focus:ring-cyan-400/10";

  return (
    <label className="block rounded-3xl border border-slate-800 bg-slate-950/45 p-4">
      <span className="flex items-center justify-between gap-3 text-sm font-semibold text-slate-100">
        {field.label}
        {field.required && <span className="text-xs text-cyan-200">Required</span>}
      </span>
      {field.help_text && <p className="mt-1 text-xs leading-5 text-slate-400">{field.help_text}</p>}

      {field.type === "select" && (
        <select className={base} value={String(value)} onChange={(event) => onChange(event.target.value)}>
          <option value="">Select an option</option>
          {field.options?.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      )}

      {(field.type === "text" || field.type === "password") && (
        <input
          className={base}
          type={field.type}
          value={String(value)}
          onChange={(event) => onChange(event.target.value)}
          placeholder={field.pattern ? "Must match policy pattern" : "Enter value"}
        />
      )}

      {field.type === "number" && (
        <input
          className={base}
          type="number"
          value={Number(value)}
          onChange={(event) => onChange(Number(event.target.value))}
        />
      )}

      {field.type === "boolean" && (
        <button
          type="button"
          onClick={() => onChange(!value)}
          className={`mt-3 flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-sm transition ${
            value
              ? "border-emerald-300/40 bg-emerald-400/10 text-emerald-100"
              : "border-slate-700 bg-slate-900 text-slate-300"
          }`}
        >
          <span>{value ? "Acknowledged" : "Click to acknowledge"}</span>
          <CheckCircle2 className="h-5 w-5" />
        </button>
      )}
    </label>
  );
}

export default function SafeOpsConsole({ scripts }: { scripts: ScriptDefinition[] }) {
  const [role, setRole] = useState<Role>("operator");
  const [selectedId, setSelectedId] = useState(scripts[0]?.id ?? "");
  const selected = useMemo(
    () => scripts.find((script) => script.id === selectedId) ?? scripts[0],
    [scripts, selectedId],
  );
  const [inputsByScript, setInputsByScript] = useState<Record<string, Record<string, unknown>>>(
    Object.fromEntries(scripts.map((script) => [script.id, initialInputs(script)])),
  );
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<"preview" | "run" | "audit" | null>(null);

  const inputs = inputsByScript[selected.id] ?? initialInputs(selected);
  const canRun = selected.allowed_roles.includes(role);

  const updateInput = (name: string, value: unknown) => {
    setInputsByScript((current) => ({
      ...current,
      [selected.id]: { ...(current[selected.id] ?? {}), [name]: value },
    }));
  };

  const submit = async (mode: "preview" | "run") => {
    setError("");
    setLoading(mode);
    try {
      const response = await executeScript(selected.id, inputs, role, mode);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(null);
    }
  };

  const loadAudit = async () => {
    setError("");
    setLoading("audit");
    try {
      setAudit(await fetchAudit(role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load audit log");
    } finally {
      setLoading(null);
    }
  };

  return (
    <main className="safeops-grid min-h-screen px-6 py-8 text-slate-100">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="glass rounded-[2rem] p-8">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-sm text-cyan-100">
              <Sparkles className="h-4 w-4" />
              Secure no-code operations console
            </div>
            <h1 className="max-w-3xl text-5xl font-black tracking-tight text-white">
              SafeOps Studio turns privileged scripts into guarded web workflows.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">
              Admins define one script and schema. Operators get validated forms, Docker sandbox policy,
              role checks, dry-run previews, and immutable audit evidence.
            </p>
          </div>

          <div className="glass rounded-[2rem] p-6">
            <p className="mb-3 text-sm font-semibold uppercase tracking-[0.25em] text-slate-400">
              Active role
            </p>
            <div className="grid gap-3">
              {roles.map((item) => (
                <button
                  key={item}
                  onClick={() => setRole(item)}
                  className={`rounded-2xl px-4 py-3 text-left text-sm font-semibold ring-1 transition ${
                    role === item ? roleBadge(item) : "bg-slate-950/60 text-slate-400 ring-slate-800"
                  }`}
                >
                  {item.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr_0.9fr]">
          <aside className="glass rounded-[2rem] p-5">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-bold">
              <FileText className="h-5 w-5 text-cyan-200" />
              Script library
            </h2>
            <div className="space-y-3">
              {scripts.map((script) => (
                <button
                  key={script.id}
                  onClick={() => {
                    setSelectedId(script.id);
                    setResult(null);
                    setError("");
                  }}
                  className={`w-full rounded-3xl border p-4 text-left transition ${
                    selected.id === script.id
                      ? "border-cyan-300/40 bg-cyan-300/10"
                      : "border-slate-800 bg-slate-950/45 hover:border-slate-600"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-bold text-white">{script.name}</span>
                    {script.approval_required && <Lock className="h-4 w-4 text-amber-200" />}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{script.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {script.tags.map((tag) => (
                      <span key={tag} className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">
                        {tag}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="glass rounded-[2rem] p-6">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-black text-white">{selected.name}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{selected.description}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-bold ring-1 ${roleBadge(role)}`}>
                {canRun ? "AUTHORIZED" : "BLOCKED"}
              </span>
            </div>

            <div className="space-y-4">
              {selected.inputs.map((field) => (
                <Field
                  key={field.name}
                  field={field}
                  value={inputs[field.name]}
                  onChange={(value) => updateInput(field.name, value)}
                />
              ))}
            </div>

            {error && (
              <div className="mt-5 rounded-2xl border border-rose-300/30 bg-rose-500/10 p-4 text-sm text-rose-100">
                {error}
              </div>
            )}

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <button
                onClick={() => submit("preview")}
                disabled={loading !== null || role === "viewer"}
                className="rounded-2xl border border-cyan-300/30 bg-cyan-300/10 px-5 py-3 font-bold text-cyan-100 transition hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-45"
              >
                {loading === "preview" ? "Generating preview..." : "Dry run preview"}
              </button>
              <button
                onClick={() => submit("run")}
                disabled={loading !== null || !canRun}
                className="rounded-2xl bg-emerald-400 px-5 py-3 font-black text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
              >
                <span className="inline-flex items-center gap-2">
                  <Play className="h-4 w-4" />
                  {loading === "run" ? "Executing..." : "Execute safely"}
                </span>
              </button>
            </div>
          </section>

          <section className="space-y-6">
            <div className="glass rounded-[2rem] p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-bold">
                <ShieldCheck className="h-5 w-5 text-emerald-200" />
                Sandbox policy
              </h2>
              <div className="grid gap-3 text-sm">
                {[
                  ["Image", selected.policy.image],
                  ["Network", selected.policy.network],
                  ["Memory", selected.policy.memory_limit],
                  ["Timeout", `${selected.policy.timeout_seconds}s`],
                  ["CPU quota", `${selected.policy.cpu_quota / 1000}%`],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between rounded-2xl bg-slate-950/55 px-4 py-3">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-semibold text-slate-100">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass rounded-[2rem] p-6">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-bold">
                <TerminalSquare className="h-5 w-5 text-cyan-200" />
                Execution output
              </h2>
              <pre className="min-h-56 overflow-auto rounded-3xl border border-slate-800 bg-black/75 p-4 text-xs leading-6 text-emerald-200">
                {result?.output ?? "Run a dry-run or execution to see sandbox output here."}
              </pre>
              {result && (
                <div className="mt-3 text-xs text-slate-400">
                  Run {result.run_id.slice(0, 8)} · {result.status} · exit {result.exit_code ?? "n/a"}
                </div>
              )}
            </div>
          </section>
        </div>

        <section className="glass mt-6 rounded-[2rem] p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-lg font-bold">
              <Activity className="h-5 w-5 text-cyan-200" />
              Immutable audit trail
            </h2>
            <button
              onClick={loadAudit}
              disabled={loading !== null}
              className="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-bold text-slate-200 transition hover:border-cyan-300/40"
            >
              {loading === "audit" ? "Loading..." : "Refresh audit"}
            </button>
          </div>
          <div className="overflow-hidden rounded-3xl border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950/80 text-xs uppercase tracking-[0.2em] text-slate-500">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Actor</th>
                  <th className="px-4 py-3">Script</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {audit.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                      Admins and viewers can refresh after executions to inspect audit events.
                    </td>
                  </tr>
                ) : (
                  audit.map((event) => (
                    <tr key={event.id} className="border-t border-slate-800 bg-slate-950/35">
                      <td className="px-4 py-3 text-slate-400">{new Date(event.timestamp).toLocaleTimeString()}</td>
                      <td className="px-4 py-3">{event.user}</td>
                      <td className="px-4 py-3">{event.script_id}</td>
                      <td className="px-4 py-3 text-emerald-200">{event.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}
