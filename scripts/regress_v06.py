"""Original 18 inspected weather failures: development regressions only."""
import argparse
import json
from pathlib import Path
from upwind.validation.research.cases import world
from evaluate_v06 import BASE, evaluate, hashes, write

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--shard',type=int,choices=range(4),required=True);a=p.parse_args()
    out=BASE/f'original18-{a.shard}';out.mkdir(exist_ok=False)
    before=hashes();original=json.loads((BASE.parent/'weather-bias/reproduced/accepted18-diagnostics.json').read_text())
    write(out/'metadata.json',{'role':'Previously inspected development regressions, not final validation','sha256_before':before})
    for old_row in original[a.shard::4]:
        seed=old_row['seed'];inv,truth=world('biased_met_campaign',seed,'final')
        truth['family']='biased_met_campaign'
        for old in (True,False):
            row=evaluate(inv,truth,old,False);row['historical_04']=dict(seed=seed,accepted=old_row['accepted'],covered=old_row['region90_covered'],map_error_m=old_row['map_error_m'])
            with (out/'results.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
            print(seed,row['model'],row['status'],row.get('accepted'),row.get('region90_covered'),flush=True)
    write(out/'completion.json',{'source_unchanged':before==hashes(),'sha256_after':hashes()})
