"""Supplementary frozen-formula controls, separate from primary inference."""
import hashlib
import json
from pathlib import Path
import numpy as np
from upwind.models import Investigation
from upwind.quality import measurement_quality
from upwind.validation.research.cases import reveal
from evaluate_v06 import BASE, ROOT, SEEDS, FAMILIES, write
from report_v06 import MODELS, dist

for i in range(4):assert (BASE/f'final-{i}/completion.json').exists()
out=BASE/'passive-controls';out.mkdir(exist_ok=False)
write(out/'metadata.json',{'role':'Supplementary controls declared after final started, not a primary selection criterion','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'protocol_sha256':hashlib.sha256((ROOT/'docs/ENGINE_V06_PASSIVE_CONTROLS.md').read_bytes()).hexdigest(),'formulas':['last-period usable observation mean','fixed10ug/m3 prior mean']})
(out/'script.py.txt').write_bytes(Path(__file__).read_bytes())
records=[]
for i in range(4):
    seed=list(SEEDS['final'])[i]
    primary=[json.loads(s) for s in (BASE/f'final-{i}/results.jsonl').read_text().splitlines()]
    for family in FAMILIES:
        raw=json.loads((BASE/f'final-{i}'/f'input-{family}-{seed}.json').read_text())
        inv=Investigation.model_validate(raw['investigation']);truth=raw['private_evaluator_truth']
        usable=measurement_quality(inv)[0];last=max(inv.study_windows,key=lambda w:w.start)
        values=[m.pm25_ug_m3 for m in usable if last.start<=m.timestamp<=last.end]
        predictions={'last_period_mean':float(np.mean(values)),'fixed_prior_mean':10.}
        # Formula locked before target outcomes are constructed.
        reveal(truth);targets=np.array(truth['target_outcomes'])
        for method,prediction in predictions.items():
            records.append({'seed':seed,'family':family,'method':method,'prediction':prediction,'rmse':float(np.sqrt(np.mean((targets-prediction)**2)))})
        for model in MODELS:
            row=next(r for r in primary if r['seed']==seed and r['family']==family and r['model']==model)
            if row.get('prediction',{}).get('status')=='scored':records.append({'seed':seed,'family':family,'method':model,'rmse':row['prediction']['rmse_ug_m3']})
with (out/'results.jsonl').open('x') as f:
    for row in records:f.write(json.dumps(row,allow_nan=False)+'\n')
summary={'controls':{m:dist([r['rmse'] for r in records if r['method']==m]) for m in ['last_period_mean','fixed_prior_mean']},'paired':{}}
lookup={(r['seed'],r['family'],r['method']):r for r in records}
for model in MODELS:
    summary['paired'][model]={}
    for method in ['last_period_mean','fixed_prior_mean']:
        blocks={};losses=0;pairs=0
        for row in records:
            if row['method']!=model:continue
            difference=row['rmse']-lookup[row['seed'],row['family'],method]['rmse']
            blocks.setdefault(row['seed'],[]).append(difference);losses+=difference>1e-10;pairs+=1
        a=np.array([np.mean(blocks[s]) for s in sorted(blocks)]);rng=np.random.default_rng(90606)
        summary['paired'][model][method]={'pairs':pairs,'unavailable_of_80':80-pairs,'losses':int(losses),'mean_rmse_difference':float(a.mean()),'bootstrap95':np.quantile(a[rng.integers(len(a),size=(5000,len(a)))].mean(axis=1),[.025,.975]).tolist()}
write(out/'summary.json',summary);write(out/'completion.json',{'scheduled_worlds':80,'control_scores':160,'engine_scores':len(records)-160})
print(json.dumps(summary,indent=2))
