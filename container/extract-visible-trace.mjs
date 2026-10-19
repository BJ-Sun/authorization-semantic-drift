#!/usr/bin/env node
import fs from "node:fs";
import { DatabaseSync } from "node:sqlite";

const dbPath = "/state/agents/main/agent/openclaw-agent.sqlite";
if (!fs.existsSync(dbPath)) {
  console.log(JSON.stringify({ events: [], error: "agent database not found" }));
  process.exit(0);
}

const db = new DatabaseSync(dbPath, { readOnly: true });
const rows = db.prepare("select seq, event_json from transcript_events order by seq").all();
const events = [];

for (const row of rows) {
  const event = JSON.parse(row.event_json);
  if (event.type !== "message" || !event.message) continue;
  const message = event.message;
  if (message.role === "assistant" && Array.isArray(message.content)) {
    for (const part of message.content) {
      if (part.type === "text") {
        events.push({ seq: row.seq, role: "assistant", type: "text", text: part.text });
      } else if (part.type === "toolCall") {
        events.push({
          seq: row.seq,
          role: "assistant",
          type: "tool_call",
          id: part.id,
          tool: part.name,
          arguments: part.arguments ?? {},
        });
      }
    }
  } else if (message.role === "toolResult") {
    const text = Array.isArray(message.content)
      ? message.content.filter((x) => x.type === "text").map((x) => x.text).join("\n")
      : String(message.content ?? "");
    events.push({
      seq: row.seq,
      role: "tool",
      type: "tool_result",
      tool_call_id: message.toolCallId,
      tool: message.toolName,
      is_error: Boolean(message.isError),
      text,
    });
  } else if (message.role === "user") {
    events.push({ seq: row.seq, role: "user", type: "text", text: message.content });
  }
}

console.log(JSON.stringify({ source: "openclaw-visible-transcript-v1", uses_hidden_reasoning: false, events }, null, 2));
