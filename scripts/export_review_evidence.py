#!/usr/bin/env python3
"""Export synthetic tool chronology and filesystem evidence without provider envelopes."""
import json
import pathlib
import re

LAB = pathlib.Path(__file__).resolve().parents[1]

def load(p):
    return json.loads(p.read_text())

def main():
    campaign = LAB / 'campaigns/cart-20261016T081032Z'
    records = []
    for job in load(campaign / 'execution-results.json'):
        if job.get('returncode') != 0:
            continue
        run = LAB / 'runs' / pathlib.Path(job['run_dir']).name
        state = load(run / 'oracle.json')
        trajectory = load(run / 'trajectory-oracle.json')
        if not state.get('authorization_semantic_drift'):
            continue
        trace = load(run / 'visible-trace.json')
        events = [e for e in trace['events'] if e.get('type') in ('tool_call', 'tool_result')]
        records.append(dict(case_id=job['case_id'], repetition=job['repetition'],
            authorization=load(run / 'case.json')['authorization'],
            user_message=load(run / 'case.json')['user_message'],
            events=events, before=load(run / 'before.json'), after=load(run / 'after.json'),
            state_oracle=state, trajectory_oracle=trajectory))
    output = dict(source_campaign=campaign.name, records=records,
                  scope='All 17 final-state findings, including the 10 registered trajectory labels. Tool events only; no hidden reasoning or provider envelope.')
    serialized = json.dumps(output, indent=2, ensure_ascii=False)
    serialized = re.sub(r'/Users/[^/\s"\x27]+/[^\s"\x27]*', '[LOCAL_PATH]', serialized)
    if re.search(r'sk-[A-Za-z0-9]{20,}', serialized):
        raise RuntimeError('Possible credential: export aborted')
    destination = LAB / 'examples/reviewer-evidence/primary-findings.json'
    destination.write_text(serialized + '\n')
    print(destination, len(records))

if __name__ == '__main__':
    main()
