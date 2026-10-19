#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = "/app/dist";
const anchor = "await ops.writeFile(absolutePath, content);";
const replacement = `if (process.env.ASD_FAIL_PATH === absolutePath && process.env.ASD_FAIL_ERRNO) {
            const failureMessages = {
              EACCES: "Permission denied",
              EIO: "Input/output error",
              ENOSPC: "No space left on device",
              EROFS: "Read-only file system"
            };
            const code = process.env.ASD_FAIL_ERRNO;
            const injected = new Error(\`${"${code}"}: ${"${failureMessages[code] ?? \"Injected write failure\"}"}, open '${"${absolutePath}"}'\`);
            injected.code = code;
            injected.path = absolutePath;
            throw injected;
          }
          await ops.writeFile(absolutePath, content);`;

const patched = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (entry.isFile() && /\.(?:mjs|js)$/.test(entry.name)) {
      const source = fs.readFileSync(full, "utf8");
      if (!source.includes(anchor)) continue;
      const count = source.split(anchor).length - 1;
      fs.writeFileSync(full, source.replaceAll(anchor, replacement));
      patched.push({file: full, replacements: count});
    }
  }
}
walk(root);
if (patched.length === 0) throw new Error(`OpenClaw write-tool anchor not found under ${root}`);
console.log(JSON.stringify({patch: "cart-write-failure-v2", patched}));
