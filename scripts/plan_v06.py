"""Predeclared equal-budget retrospective planning, locked before reveal."""
import argparse
import copy
import hashlib
from itertools import combinations
import json
from pathlib import Path
import time
import numpy as np
from upwind.inference import fit
from upwind.engine import eligible_indices, select_plan
from upwind.models import Investigation, Measurement
from upwind.prediction_design import prediction_score
from upwind.numerics import flow_vector
from upwind.validation.research.cases import reveal
from upwind.validation.research.run import score_prediction
from evaluate_v06 import BASE, hashes, write, metrics, targets


def run(out,shard):
    frozen=json.loads((out/'freeze.json').read_text());before=hashes()
    assert before==frozen['sha256']
    folder=out/f'planning-{shard}';folder.mkdir(exist_ok=False)
    started=time.perf_counter()
    for family in ['characterized_nominal','shared_reference_bias','independent_transport']:
        source=out/f'final-{shard}'/f'input-{family}-{7300000+shard}.json'
        raw=json.loads(source.read_text());inv=Investigation.model_validate(raw['investigation']);truth=raw['private_evaluator_truth']
        f=fit(inv,diagnostics=False);eligible=[i for i in eligible_indices(inv) if f['candidate_supported'][i]]
        score,_=prediction_score(inv,f)
        subsets=[()] + [s for n in [1,2] for s in combinations(eligible,n) if sum(inv.sites[i].cost for i in s)<=inv.settings.budget+1e-8]
        best=min(subsets,key=lambda s:(-round(score(list(s)),12),sum(inv.sites[i].cost for i in s),tuple(inv.sites[i].id for i in s)))
        flow=flow_vector(f['wind']);center=f['source_xy'].mean(axis=0)
        def priority(i):
            delta=f['site_xy'][i]-center
            return abs(delta[0]*flow[1]-delta[1]*flow[0])-.05*np.dot(delta,flow)
        wind=sorted(eligible,key=lambda i:(priority(i),inv.sites[i].id))
        locked={'prediction_variance':list(best),
                'spread':select_plan(inv,'spread',lambda x:0,eligible,np.random.default_rng(90606)),
                'random':select_plan(inv,'random',lambda x:0,eligible,np.random.default_rng(90606)),
                'wind':select_plan(inv,'wind',lambda x:0,wind,np.random.default_rng(90606))}
        locked={name:[inv.sites[i].id for i in indices] for name,indices in locked.items()}
        write(folder/f'locked-{family}.json',{'seed':truth['seed'],'plans':locked,'information':'Observable investigation only; no oracle wind, source or outcomes','input_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
        lock=hashlib.sha256((folder/f'locked-{family}.json').read_bytes()).hexdigest()
        reveal(truth)  # No candidate or target outcomes exist in the locked policies.
        for name,ids in locked.items():
            updated=inv.model_copy(deep=True);cost=0.
            for id in ids:
                site=next(s for s in inv.sites if s.id==id);j=int(id[1:]);cost+=site.cost
                updated.measurements.append(Measurement(sensor_id='followup-'+id,timestamp=truth['last_timestamp'],pm25_ug_m3=float(truth['candidate_outcomes'][j]),uncertainty_ug_m3=float(truth['future_sigma'][j]),latitude=site.latitude,longitude=site.longitude,origin='synthetic'))
            assert cost<=250+1e-8 and len(ids)<=2
            row={'family':family,'seed':truth['seed'],'method':name,'site_ids':ids,'cost':cost,'equipment':len(ids),'locked_sha256':lock}
            try:
                updated_fit=fit(updated,diagnostics=False)
                row.update(status='fitted',**metrics(updated_fit,truth,False),prediction=score_prediction(updated_fit,targets(truth),truth['target_outcomes']))
            except ValueError as exc:row.update(status='refused',reason=str(exc))
            except Exception as exc:row.update(status='crash',reason=f'{type(exc).__name__}: {exc}')
            with (folder/'results.jsonl').open('a') as file:file.write(json.dumps(row,allow_nan=False)+'\n')
            print(truth['seed'],family,name,row['status'],cost,flush=True)
    write(folder/'completion.json',{'source_unchanged':before==hashes(),'sha256_after':hashes(),'seconds':time.perf_counter()-started,'rows':12})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=BASE);p.add_argument('--shard',type=int,choices=range(4),required=True);a=p.parse_args();run(a.out,a.shard)
