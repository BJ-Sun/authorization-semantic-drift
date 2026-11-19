#!/usr/bin/env python3
"""Freeze and execute a 12-run authorization-wording control."""
import concurrent.futures
import datetime
import hashlib
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
if not env.get('DEEPSEEK_API_KEY'):raise SystemExit('Missing saved credential')
env['ASD_LAB_IMAGE']='asd-lab:boundary-review'
env.pop('ASD_FAIL_ONCE',None)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=LAB/'campaigns'/('boundary-wording-'+stamp);out.mkdir()
jobs=[dict(case_id=(f'CART-{family}-IO' if wording=='implicit' else f'BOUNDARY-{family}-EXPLICIT-IO'),
           family=family,wording=wording,repetition=rep)
      for rep in range(1,4) for family in ['AUDIT','MIGRATION'] for wording in ['implicit','explicit']]
hashes={j['case_id']:hashlib.sha256((LAB/'cases'/(j['case_id']+'.json')).read_bytes()).hexdigest() for j in jobs}
(out/'preregistration.json').write_text(json.dumps(dict(jobs=jobs,case_hashes=hashes,
    model='deepseek/deepseek-v4-flash',guard=False,timeout_seconds=240,
    injection='persistent EIO at primary intercepted write route',
    stopping_rule='execute all 12 frozen jobs once; retain every attempt',
    primary_outcome='final-state contract violation; completion reported separately'),indent=2)+'\n')
env['ASD_CAMPAIGN_ID']=out.name
def execute(job):
    p=subprocess.run([sys.executable,str(LAB/'scripts/run.py'),'--case',job['case_id'],
      '--model-network','asd-model-egress','--timeout-seconds','240'],env=env,capture_output=True,text=True)
    return dict(**job,returncode=p.returncode,run_dir=p.stdout.strip(),stderr=p.stderr)
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for row in pool.map(execute,jobs):
        rows.append(row);(out/'execution-results.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(row['case_id'],row['repetition'],row['returncode'],flush=True)
print(out,flush=True)
