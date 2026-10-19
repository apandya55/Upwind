"""Fixed post-primary source-observability control; model remains frozen."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
from upwind.models import Investigation
from upwind.validation import weather_bias as wb
from evaluate_v06 import BASE, ROOT, hashes, evaluate, write

SEEDS=range(7700000,7700016)

def run(shard):
    assert all((BASE/f'final-{i}/completion.json').exists() for i in range(4))
    before=hashes();assert before==json.loads((BASE/'freeze.json').read_text())['sha256']
    folder=BASE/f'observability-{shard}';folder.mkdir(exist_ok=False)
    write(folder/'metadata.json',{'protocol':'UW-ENGINE-2026-06-O','role':'Post-primary supplementary experiment, no model selection','sha256_before':before,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((ROOT/'docs/ENGINE_V06_OBSERVABILITY_CONTROL.md').read_bytes()).hexdigest(),'seeds':list(SEEDS)[shard::4]})
    shutil.copyfile(__file__,folder/'script.py.txt')
    started=time.perf_counter()
    for seed in list(SEEDS)[shard::4]:
        rng=np.random.default_rng(seed+19000000)
        layout=[(20.,-190.),(60.,-75.),(125.,95.),(190.,205.),(300.,-135.),(450.,40.)]
        angles=(np.array([248.,263.,279.,296.])+rng.uniform(-3,3,4)).tolist()
        previous_layout,previous_angles=wb.LAYOUTS['final'],wb.ANGLES['final']
        try:
            wb.LAYOUTS['final'],wb.ANGLES['final']=layout,angles
            original,truth=wb.world('characterized_nominal',seed,'final')
        finally:wb.LAYOUTS['final'],wb.ANGLES['final']=previous_layout,previous_angles
        bias=float(rng.uniform(36,52))*(1 if seed%2==0 else -1)
        for family in ['near_nominal','near_shared_bias']:
            inv=original.model_copy(deep=True);state=dict(truth,family=family,control_protocol='UW-ENGINE-2026-06-O',injected_common_bias_deg=bias if family.endswith('bias') else 0.)
            if family.endswith('bias'):
                for w in inv.weather:w.wind_from_deg=float((w.wind_from_deg+bias)%360)
            inv.name=f'SYNTHETIC post-primary observability {family} {seed}'
            inv=Investigation.model_validate(inv.model_dump())
            write(folder/f'input-{family}-{seed}.json',{'investigation':inv.model_dump(),'private_evaluator_truth':state})
            for old in [True,False]:
                row=evaluate(inv,state,old,False)
                with (folder/'results.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
                print(seed,family,row['model'],row['status'],row.get('accepted'),row.get('region90_covered'),flush=True)
    write(folder/'completion.json',{'sha256_after':hashes(),'source_unchanged':before==hashes(),'seconds':time.perf_counter()-started})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--shard',type=int,choices=range(4),required=True);run(p.parse_args().shard)
