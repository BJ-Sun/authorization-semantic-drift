#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = "/state";
const files = {};
function walk(dir) {
  if (!fs.existsSync(dir)) return;
  for (const name of fs.readdirSync(dir).sort()) {
    const full = path.join(dir, name);
    const st = fs.lstatSync(full);
    if (st.isDirectory()) walk(full);
    else if (st.isFile() && st.size <= 2_000_000 && /\.(json|jsonl|log|txt)$/i.test(name)) {
      files[path.relative(root, full)] = fs.readFileSync(full, "utf8");
    }
  }
}
walk(root);
console.log(JSON.stringify({root, files}));

