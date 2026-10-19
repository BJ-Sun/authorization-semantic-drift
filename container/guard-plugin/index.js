import fs from "node:fs";
import {definePluginEntry} from "openclaw/plugin-sdk/plugin-entry";
import {evaluateToolCall} from "./guard-policy.js";

const caseId = process.env.ASD_CASE_ID;
if (!caseId || !/^[A-Za-z0-9-]+$/.test(caseId)) {
  throw new Error("ASD Authorization Guard requires a valid ASD_CASE_ID");
}
const spec = JSON.parse(fs.readFileSync(`/opt/asd-lab/cases/${caseId}.json`, "utf8"));
const auditPath = "/state/asd-guard-audit.ndjson";

function audit(event, decision) {
  fs.appendFileSync(auditPath, JSON.stringify({
    sequence_time: new Date().toISOString(),
    case_id: caseId,
    tool: event.toolName,
    tool_call_id: event.toolCallId ?? null,
    decision: decision.allow ? "allow" : "block",
    reason: decision.reason,
    candidates: decision.candidates ?? [],
  }) + "\n");
}

export default definePluginEntry({
  id: "asd-authorization-guard",
  name: "ASD Authorization Guard",
  description: "Pre-commit enforcement of the frozen ASD case contract.",
  register(api) {
    api.on("before_tool_call", (event) => {
      const decision = evaluateToolCall(event.toolName, event.params, spec.authorization);
      audit(event, decision);
      if (decision.allow) return;
      return {
        block: true,
        blockReason: `AUTHORIZATION_REQUIRED: ${decision.reason}. The proposed state change exceeds the frozen user contract; request explicit authorization for the new target or effect.`,
      };
    });
  },
});
