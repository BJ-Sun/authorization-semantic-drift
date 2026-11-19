import fs from 'node:fs';
import path from 'node:path';
let count=0;
function walk(dir) {
  for(const e of fs.readdirSync(dir,{withFileTypes:true})) {
    const p=path.join(dir,e.name);
    if(e.isDirectory()) walk(p);
    else if(/\.(js|mjs)$/.test(e.name)) {
      const s=fs.readFileSync(p,'utf8');
      const anchor='if (process.env.ASD_FAIL_PATH === absolutePath && process.env.ASD_FAIL_ERRNO) {';
      if(s.includes(anchor)) {
        const replacement=`if (process.env.ASD_FAIL_PATH === absolutePath && process.env.ASD_FAIL_ERRNO && !(process.env.ASD_FAIL_ONCE === '1' && (globalThis.__cartFailedPaths ??= new Set()).has(absolutePath))) {\n (globalThis.__cartFailedPaths ??= new Set()).add(absolutePath);`;
        fs.writeFileSync(p,s.replaceAll(anchor,replacement)); count++;
      }
    }
  }
}
walk('/app/dist');
if(!count) throw new Error('No injection anchor found');
console.log(JSON.stringify({patched:count}));
