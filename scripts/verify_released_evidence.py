#!/usr/bin/env python3
"""Recompute state labels from released contracts and snapshots, without model access."""
import json
import pathlib
import subprocess
import sys
import tempfile

LAB=pathlib.Path(__file__).resolve().parents[1]
def main():
    checked=0
    for name in ['primary-findings.json','boundary-wording-findings.json']:
        records=json.loads((LAB/'examples/reviewer-evidence'/name).read_text())['records']
        for record in records:
            with tempfile.TemporaryDirectory(prefix='cart-verify-') as directory:
                root=pathlib.Path(directory)
                values=[dict(id=record['case_id'],authorization=record['authorization']),record['before'],record['after']]
                paths=[]
                for i,value in enumerate(values):
                    p=root/f'{i}.json';p.write_text(json.dumps(value));paths.append(str(p))
                output=subprocess.check_output([sys.executable,str(LAB/'scripts/oracle.py'),*paths],text=True)
                actual=json.loads(output);expected=record['state_oracle']
                for field in ['authorization_semantic_drift','violations','effects','security_impacts']:
                    assert actual[field]==expected[field],(name,record['case_id'],record['repetition'],field)
                checked+=1
    subprocess.run([sys.executable,str(LAB/'scripts/audit_primary_witnesses.py')],check=True)
    print(f'Verified {checked} released state records and ten primary scope-witness links')
if __name__=='__main__':main()
