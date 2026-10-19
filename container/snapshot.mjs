#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const root = "/workspace";
const entries = {};
function walk(dir) {
  for (const name of fs.readdirSync(dir).sort()) {
    const full = path.join(dir, name);
    const rel = path.relative(root, full);
    const st = fs.lstatSync(full);
    const item = {type: st.isDirectory() ? "directory" : st.isSymbolicLink() ? "symlink" : "file", mode: (st.mode & 0o7777).toString(8).padStart(4, "0"), uid: st.uid, gid: st.gid, size: st.size};
    if (st.isFile()) item.sha256 = crypto.createHash("sha256").update(fs.readFileSync(full)).digest("hex");
    if (st.isSymbolicLink()) item.target = fs.readlinkSync(full);
    entries[rel] = item;
    if (st.isDirectory()) walk(full);
  }
}
walk(root);
console.log(JSON.stringify({root, entries}, null, 2));

