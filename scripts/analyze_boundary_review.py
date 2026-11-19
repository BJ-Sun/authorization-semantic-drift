#!/usr/bin/env python3
"""Summarize every frozen wording-control attempt using visible outcomes."""
import argparse
import collections
import json
import pathlib
from analyze_guard_campaign import classify, visible_final

LAB=pathlib.Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('campaign_id');args=ap.parse_args()
    campaign=LAB/'campaigns'/args.campaign_id
    executions=load(campaign/'execution-results.json');rows=[]
    for e in executions:
        row={k:e[k] for k in ['case_id','family','wording','repetition','returncode']}
        run=LAB/'runs'/pathlib.Path(e['run_dir']).name
        if e['returncode'] or not (run/'oracle.json').exists():
            row['valid']=False
            stderr=(run/'agent.stderr.log').read_text() if (run/'agent.stderr.log').exists() else ''
            row['incomplete_reason']='provider_idle_timeout' if 'idle timeout' in stderr else 'execution_failure'
            if (run/'oracle.json').exists():
                row['partial_snapshot_violation']=bool(load(run/'oracle.json')['authorization_semantic_drift'])
            rows.append(row);continue
        state=load(run/'oracle.json');after=load(run/'after.json')['entries']
        target=load(run/'case.json')['authorization']['may_create_or_replace'][0].removeprefix('/workspace/')
        violation=bool(state['authorization_semantic_drift']);created=target in after
        row.update(valid=True,run_id=run.name,target_created=created,
            unauthorized_state_change=violation,
            registered_failure_observed=load(run/'trajectory-oracle.json')['ordinary_failure_observed'],
            task_outcome=classify(created,violation,visible_final(load(run/'agent.stdout.json'))))
        rows.append(row)
    cells={}
    for key in sorted({r['case_id'] for r in rows}):
        selected=[r for r in rows if r['case_id']==key];valid=[r for r in selected if r['valid']]
        cells[key]=dict(attempts=len(selected),valid=len(valid),
            failure_observed=sum(r['registered_failure_observed'] for r in valid),
            target_created=sum(r['target_created'] for r in valid),
            violations=sum(r['unauthorized_state_change'] for r in valid),
            outcomes=dict(collections.Counter(r['task_outcome'] for r in valid)))
    result=dict(campaign_id=args.campaign_id,cells=cells,rows=rows,
        protocol='12 frozen jobs; all attempts retained; no external monitor comparison',uses_hidden_reasoning=False)
    (campaign/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(cells,indent=2))
if __name__=='__main__':main()
