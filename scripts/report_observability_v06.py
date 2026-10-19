import json,sys
from pathlib import Path
sys.path.insert(0,'scripts')
from report_v06 import summarize,MODELS
b=Path('evaluations/engine-v06');rows=[]
for i in range(4):rows += [json.loads(s) for s in (b/f'observability-{i}/results.jsonl').read_text().splitlines()]
assert len(rows)==64
summary={f:{m:summarize([r for r in rows if r['family']==f and r['model']==m]) for m in MODELS} for f in ['near_nominal','near_shared_bias']}
(b/'observability-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
out=['# Supplementary observability control results','','Post-primary UW-ENGINE-2026-06-O: 16 paired seeds, two conditions, two engines; **64 attempts**. Unchanged frozen scientific source. This deliberately more observable geometry does not replace the primary comparison or its failed 50m targets. All inputs are synthetic.','','| Condition | Model | Fits | Accepted | Accepted wrong | Region coverage | Median mean error m | Mean region/domain |','|---|---|---:|---:|---:|---:|---:|---:|']
for f,models in summary.items():
 for m,s in models.items():
  out.append(f"| {f} | {m} | {s['fitted']}/16 | {s['accepted']['k']}/16 | {s['accepted_wrong']['k']}/{s['accepted_wrong']['n']} | {s['coverage']['k']}/{s['coverage']['n']} | {s['mean_error_m']['median']:.1f} | {s['area']['mean']:.1%} |")
out+=['','Wrong includes accepted region misses or false source alarms. See [raw summary](../evaluations/engine-v06/observability-summary.json) for all distributions and Wilson intervals, and [protocol](ENGINE_V06_OBSERVABILITY_CONTROL.md) for geometry and weather biases. Common-bias failures remain; do not claim general reliability from nominal performance. No parameter or acceptance-rule tuning followed this control.']
Path('docs/ENGINE_V06_OBSERVABILITY_RESULTS.md').write_text('\n'.join(out)+'\n');print('\n'.join(out))
