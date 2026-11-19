#!/usr/bin/env python3
"""Retain two exploratory live controls; never print credentials."""
import datetime
import json
import os
import pathlib
import subprocess
import sys
LAB=pathlib.Path(__file__).resolve().parents[1]
env=dict(os.environ)
for line in (LAB/'.env').read_text().splitlines():
    if line.startswith('DEEPSEEK_API_KEY='):
        env['DEEPSEEK_API_KEY']=line.split('=',1)[1].strip().strip('"\x27')
if not env.get('DEEPSEEK_API_KEY'): raise SystemExit('Missing stored DeepSeek credential')
env.update(ASD_LAB_IMAGE='asd-lab:transient-review',ASD_FAIL_ONCE='1')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=LAB/'campaigns'/('transient-live-'+stamp);out.mkdir()
jobs=['CART-AUDIT-IO','CART-MIGRATION-IO']
(out/'preregistration.json').write_text(json.dumps(dict(jobs=jobs,guard_mode='strict',
    injection='first intercepted write only; preload disabled',
    purpose='exploratory original-contract recovery control',model='deepseek/deepseek-v4-flash'),indent=2))
rows=[]
for case in jobs:
    p=subprocess.run([sys.executable,str(LAB/'scripts/run.py'),'--case',case,
       '--model-network','asd-model-egress','--authorization-guard','--guard-mode','strict',
       '--timeout-seconds','240'],env=env,capture_output=True,text=True)
    rows.append(dict(case_id=case,repetition=1,returncode=p.returncode,run_dir=p.stdout.strip(),stderr=p.stderr))
    (out/'execution-results.json').write_text(json.dumps(rows,indent=2))
    print(case,p.returncode,p.stdout.strip(),flush=True)
print(out)
