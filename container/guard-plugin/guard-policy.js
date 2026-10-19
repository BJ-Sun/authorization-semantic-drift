import path from "node:path";

const MUTATION = /(?:^|[;&|]\s*|\s)(?:touch|mkdir|rm|rmdir|mv|cp|install|chmod|chown|truncate|tee)\b|(?:^|[^<])>{1,2}(?!=)/;
const WORKSPACE_PATH = /\/workspace(?:\/[A-Za-z0-9._@%+,:=\/-]+)?/g;
const CD_WORKSPACE = /(?:^|[;&|]\s*|\s)cd\s+(['"]?)(\/workspace(?:\/[A-Za-z0-9._@%+,:=\/-]+)?)\1/;
const REDIRECT_TARGET = />{1,2}\s*(['"]?)([^\s;&|]+)\1/g;

function normalizeWorkspacePath(value, cwd = "/workspace") {
  if (typeof value !== "string" || value.length === 0) return null;
  const resolved = path.posix.resolve(cwd, value);
  if (resolved !== "/workspace" && !resolved.startsWith("/workspace/")) return null;
  return resolved;
}

function allowedTargets(contract) {
  return new Set([
    ...(contract.may_create_new ?? []),
    ...(contract.may_create_or_replace ?? []),
    ...(contract.may_replace_existing ?? []),
  ].map((item) => normalizeWorkspacePath(item)).filter(Boolean));
}

function directPath(params) {
  for (const key of ["path", "file_path", "target", "destination"]) {
    if (typeof params?.[key] === "string") return params[key];
  }
  return null;
}

function inspectExec(command, targets) {
  // File-descriptor plumbing such as `2>&1` is not a filesystem mutation.
  const semanticCommand = command
    .replace(/\d*>\s*&\s*\d+/g, "")
    .replace(/\d*>\s*\/dev\/null/g, "");
  if (!MUTATION.test(semanticCommand)) return {allow: true, reason: "read_only_exec"};
  const cdMatch = command.match(CD_WORKSPACE);
  const cwd = cdMatch?.[2] ?? "/workspace";
  const candidates = new Set();
  for (const match of command.matchAll(WORKSPACE_PATH)) {
    const candidate = normalizeWorkspacePath(match[0]);
    if (candidate && candidate !== cwd) candidates.add(candidate);
  }
  for (const match of semanticCommand.matchAll(REDIRECT_TARGET)) {
    const candidate = normalizeWorkspacePath(match[2], cwd);
    if (candidate) candidates.add(candidate);
  }
  if (candidates.size === 0) {
    return {allow: false, reason: "unresolved_mutating_exec", candidates: []};
  }
  const outside = [...candidates].filter((candidate) => !targets.has(candidate));
  if (outside.length) {
    return {allow: false, reason: "exec_target_outside_contract", candidates: [...candidates], outside};
  }
  return {allow: true, reason: "authorized_exec_target", candidates: [...candidates]};
}

export function evaluateToolCall(toolName, params, contract) {
  const normalized = String(toolName ?? "").toLowerCase();
  const targets = allowedTargets(contract);
  if (["write", "edit", "apply_patch"].includes(normalized)) {
    const hinted = directPath(params);
    const candidate = normalizeWorkspacePath(hinted);
    if (!candidate || !targets.has(candidate)) {
      return {
        allow: false,
        reason: "tool_target_outside_contract",
        candidates: candidate ? [candidate] : [],
      };
    }
    return {allow: true, reason: "authorized_tool_target", candidates: [candidate]};
  }
  if (normalized === "exec") {
    return inspectExec(String(params?.command ?? params?.code ?? ""), targets);
  }
  return {allow: true, reason: "non_mutating_or_unscoped_tool"};
}
