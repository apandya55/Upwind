"""Derived reporting only. Refuses incomplete or source-drifted final evidence."""
import hashlib
import json
from pathlib import Path
from collections import Counter
import numpy as np
from upwind.validation.research.run import wilson
from evaluate_v06 import BASE, ROOT, FAMILIES, SEEDS, hashes, write

MODELS=['plume-weather-0.5.0','plume-robust-0.6.0']

def read(path):return json.loads(path.read_text())
def lines(path):return [json.loads(s) for s in path.read_text().splitlines()]
def dist(values):
    a=np.array([v for v in values if v is not None],float)
    return None if not len(a) else dict(n=len(a),median=float(np.median(a)),p90=float(np.quantile(a,.9)),mean=float(a.mean()),max=float(a.max()),rms=float(np.sqrt(np.mean(a*a))))
def ratio(k,n):return dict(k=k,n=n,rate=k/n if n else None,wilson95=list(wilson(k,n)) if n else None)
def summarize(rows):
    fitted=[r for r in rows if r['status']=='fitted'];present=[r for r in fitted if r['source_present']];accepted=[r for r in fitted if r['accepted']]
    wrong=[r for r in accepted if not r['source_present'] or not r['region90_covered']]
    return dict(attempts=len(rows),fitted=len(fitted),refusals=sum(r['status']=='refused' for r in rows),crashes=sum(r['status']=='crash' for r in rows),numeric_failures=sum(r.get('numeric_ok') is False for r in rows),
        accepted=ratio(len(accepted),len(rows)),accepted_wrong=ratio(len(wrong),len(accepted)),accepted_wrong_all=ratio(len(wrong),len(rows)),
        accepted_geographic_misses=sum(r['source_present'] and not r['region90_covered'] for r in accepted),accepted_false_source_alarms=sum(not r['source_present'] for r in accepted),
        coverage=ratio(sum(r['region90_covered'] for r in present),len(present)),area=dist([r['region90_area_fraction'] for r in fitted]),accepted_area=dist([r['region90_area_fraction'] for r in accepted]),
        map_error_m=dist([r['map_error_m'] for r in present]),mean_error_m=dist([r['mean_error_m'] for r in present]),
        accepted_map_error_m=dist([r['map_error_m'] for r in accepted]),accepted_mean_error_m=dist([r['mean_error_m'] for r in accepted]),
        source_brier=dist([r['source_brier'] for r in fitted]),wall_seconds=dist([r['wall_ms']/1000 for r in rows]),
        reasons=dict(Counter(r['reason'] for r in rows if r['status']!='fitted')))

def paired(rows,key,square=False):
    lookup={(r['model'],r['family'],r['seed']):r for r in rows}
    by_seed={};pairs=0
    for r in rows:
        if r['model']!=MODELS[0]:continue
        other=lookup.get((MODELS[1],r['family'],r['seed']))
        if not other or r['status']!='fitted' or other['status']!='fitted':continue
        a=r.get(key);b=other.get(key)
        if a is None or b is None:continue
        by_seed.setdefault(r['seed'],[]).append(b*b-a*a if square else b-a);pairs+=1
    values=np.array([np.mean(by_seed[s]) for s in sorted(by_seed)])
    if not len(values):return None
    rng=np.random.default_rng(90606);draws=values[rng.integers(len(values),size=(5000,len(values)))].mean(axis=1)
    return dict(pairs=pairs,seed_blocks=len(values),candidate_minus_baseline=float(values.mean()),bootstrap95=np.quantile(draws,[.025,.975]).tolist(),meaning='Paired seed-block mean loss difference; negative favours candidate. Conditions within a block are correlated; this is not operational prevalence.')

def main():
    frozen=read(BASE/'freeze.json');assert hashes()==frozen['sha256'],'Current source differs from candidate freeze'
    rows=[];plans=[];calibration=[];original=[]
    for stage,target in [('final',rows),('calibration',calibration),('original18',original),('planning',plans)]:
        for i in range(4):
            folder=BASE/f'{stage}-{i}';complete=read(folder/'completion.json')
            assert complete['source_unchanged'],str(folder)
            assert complete['sha256_after']==frozen['sha256'],str(folder)
            target.extend(lines(folder/'results.jsonl'))
    expected={(m,f,s) for m in MODELS for f in FAMILIES for s in SEEDS['final']}
    assert {(r['model'],r['family'],r['seed']) for r in rows}==expected and len(rows)==960
    assert len(calibration)==128 and len(original)==36 and len(plans)==48
    per={family:{m:summarize([r for r in rows if r['family']==family and r['model']==m]) for m in MODELS} for family in FAMILIES}
    prediction={}
    for m in MODELS:
        scheduled=[r for r in rows if r['model']==m and r['prediction_scheduled']]
        scored=[r['prediction'] for r in scheduled if r.get('prediction',{}).get('status')=='scored']
        assert len(scheduled)==80
        prediction[m]=dict(scheduled=len(scheduled),scored=len(scored),unavailable=len(scheduled)-len(scored),**{k:dist([p[k] for p in scored]) for k in ['rmse_ug_m3','nlpd','interval90_coverage','interval90_width']})
    prediction_rows=[]
    for r in rows:
        if r.get('prediction',{}).get('status')=='scored':prediction_rows.append(dict(r,passive_rmse=r['prediction']['rmse_ug_m3']))
    planning={}
    for family in ['characterized_nominal','shared_reference_bias','independent_transport']:
        subset=[r for r in plans if r['family']==family];by={(r['seed'],r['method']):r for r in subset}
        planning[family]={method:dict(attempts=4,fitted=sum(r['status']=='fitted' for r in subset if r['method']==method),actual_cost=dist([r['cost'] for r in subset if r['method']==method]),rmse=dist([r['prediction']['rmse_ug_m3'] for r in subset if r['method']==method and r['status']=='fitted'])) for method in ['prediction_variance','spread','random','wind']}
        for control in ['spread','random','wind']:
            differences=[]
            for seed in list(SEEDS['final'])[:4]:
                a,b=by[seed,'prediction_variance'],by[seed,control]
                if a['status']=='fitted' and b['status']=='fitted':differences.append(a['prediction']['rmse_ug_m3']-b['prediction']['rmse_ug_m3'])
            x=np.array(differences);rng=np.random.default_rng(90606)
            planning[family]['versus_'+control]=dict(paired_worlds=len(x),losses=int(np.sum(x>1e-10)),ties=int(np.sum(abs(x)<=1e-10)),mean_difference=float(x.mean()) if len(x) else None,bootstrap95=np.quantile(x[rng.integers(len(x),size=(5000,len(x)))].mean(axis=1),[.025,.975]).tolist() if len(x) else None)
    nominal=per['characterized_nominal'][MODELS[1]]
    summary=dict(protocol='UW-ENGINE-2026-06',models=MODELS,attempts=960,condition_worlds=480,paired_seed_blocks=24,
        overall={m:summarize([r for r in rows if r['model']==m]) for m in MODELS},per_condition=per,
        paired_absolute_map=paired(rows,'map_error_m'),paired_absolute_mean=paired(rows,'mean_error_m'),paired_squared_mean=paired(rows,'mean_error_m',True),paired_passive_rmse=paired(prediction_rows,'passive_rmse'),
        passive_prediction=prediction,planning=planning,
        calibration={m:summarize([r for r in calibration if r['model']==m]) for m in MODELS},original18={m:summarize([r for r in original if r['model']==m]) for m in MODELS},
        nominal_50m_map_target_pass=nominal['map_error_m']['median']<=50,nominal_50m_mean_target_pass=nominal['mean_error_m']['median']<=50,
        common_bias_fewer_accepted_errors=per['shared_reference_bias'][MODELS[1]]['accepted_wrong']['k']<per['shared_reference_bias'][MODELS[0]]['accepted_wrong']['k'])
    write(BASE/'summary.json',summary)
    output=['# Engine 0.6 — comparative stress results','',
        'Frozen protocol [UW-ENGINE-2026-06](ENGINE_V06_PROTOCOL.md); [implementation and equations](ENGINE_V06_IMPLEMENTATION.md). Both engines received identical observable inputs. **Synthetic evidence only; no measured field accuracy or organizational attribution readiness is established.**','',
        'Exact source/configuration: [49-file freeze](../evaluations/engine-v06/freeze.json), [archived source](../evaluations/engine-v06/frozen-source), [baseline manifest](../evaluations/engine-v06/baseline-manifest.json). The stage named calibration was an assessment; no probability calibration transform or revised threshold was fitted.','',
        '## Fresh final comparison','',
        '480 condition-worlds across 24 paired seed blocks and 20 conditions; 960 source-fit attempts. Refusals and crashes remain in the attempt denominators. Conditional geographic coverage, point error, region area and acceptance answer different questions. The table reports medians of the posterior-mean and density-mode Euclidean errors, including fitted source-present worlds.','',
        '| Condition | Engine | Fit / attempts | Accepted | Wrong / accepted | Covered / source fits | Median mean / mode error (m) | Mean region % |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    def val(d,key):return f"{d[key]['median']:.1f}" if d[key] else '—'
    for family,models in per.items():
        for m,d in models.items():
            output.append(f"| {family} | {m.split('-')[-1]} | {d['fitted']}/{d['attempts']} | {d['accepted']['k']} | {d['accepted_wrong']['k']}/{d['accepted_wrong']['n']} | {d['coverage']['k']}/{d['coverage']['n']} | {val(d,'mean_error_m')} / {val(d,'map_error_m')} | {100*d['area']['mean']:.1f} |" if d['area'] else f"| {family} | {m.split('-')[-1]} | 0/{d['attempts']} | 0 | 0/0 | — | — | — |")
    output+=['','All per-condition Wilson95% intervals and accepted-only error/area distributions are in [summary.json](../evaluations/engine-v06/summary.json). `Wrong` counts accepted source-present regions missing truth plus any accepted background-only false source alarms; geographic misses and false alarms are also stored separately. These contrived conditions are not an operational mixture; do not turn the pooled fraction into an accuracy claim.','', '## Predeclared targets and paired losses','']
    output += [f"- Characterized nominal overall median density-mode error ≤50m: **{'PASS' if summary['nominal_50m_map_target_pass'] else 'FAIL'}** ({nominal['map_error_m']['median']:.1f}m).",f"- Characterized nominal overall median posterior-mean error ≤50m: **{'PASS' if summary['nominal_50m_mean_target_pass'] else 'FAIL'}** ({nominal['mean_error_m']['median']:.1f}m).",f"- Fewer accepted shared-reference-bias errors: **{'PASS' if summary['common_bias_fewer_accepted_errors'] else 'FAIL'}**. Useful nominal acceptance must be considered alongside this count."]
    for key in ['paired_absolute_map','paired_absolute_mean','paired_squared_mean','paired_passive_rmse']:
        d=summary[key]
        if d:output.append(f"- {key}: candidate minus baseline {d['candidate_minus_baseline']:.3f}; seed-block bootstrap95% [{d['bootstrap95'][0]:.3f}, {d['bootstrap95'][1]:.3f}], {d['seed_blocks']} blocks/{d['pairs']} paired worlds. Negative favours candidate. Squared location units are m², absolute location m, passive RMSE µg/m³.")
    output+=['','## Passive concentration prediction','', '| Engine | Scored / scheduled | Mean world RMSE µg/m³ | Mean NLPD | Mean interval coverage | Mean interval width µg/m³ |','|---|---:|---:|---:|---:|---:|']
    for m,d in prediction.items():output.append(f"| {m} | {d['scored']}/{d['scheduled']} | {d['rmse_ug_m3']['mean']:.3f} | {d['nlpd']['mean']:.3f} | {d['interval90_coverage']['mean']:.3f} | {d['interval90_width']['mean']:.3f} |")
    output+=['','Each world has12 correlated target outcomes. Unavailable weather fits remain in the80 scheduled cases per engine. Predictions are retrospective at the last observed timestamp, not forecasts.','', '## Equal-budget downstream planning','',
        '12 paired worlds (four seeds in each of three conditions), four locked methods and48 actual downstream candidate fits. All policies receive identical initial pollution/weather records and permissible candidates. All updates use the candidate engine. Maximum250 cost units/two instruments; actual spending is stored. Choices were saved and hashed before outcomes were revealed. Weather hardware/time is not free or included.','',
        '| Condition | Comparator | Paired worlds | Prediction planner losses | Mean RMSE difference | Paired bootstrap95% |','|---|---|---:|---:|---:|']
    for family,data in planning.items():
        for control in ['spread','random','wind']:
            d=data['versus_'+control];ci=d['bootstrap95'];output.append(f"| {family} | {control} | {d['paired_worlds']} | {d['losses']} | {d['mean_difference']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] |" if ci else f"| {family} | {control} | 0 | — | — | — |")
    output+=['','Negative differences favour the prediction planner. Four worlds per condition provide weak evidence about tails; losses remain visible and no general planner superiority follows. Concentration gains do not establish source-attribution accuracy.','', '## Original 18 failures: inspected regression only','',
        'The original0.4 results are retained and reproduced separately. All18 original accepted regions missed truth. Both0.5 and0.6 were rerun on those same observed campaigns; these cases are development-used, not fresh final evidence.','', '| Seed | 0.4 accepted / covered | 0.5 accepted / covered | 0.6 accepted / covered | 0.6 mean / mode error (m) |','|---|---|---|---|---:|']
    grouped={(r['seed'],r['model']):r for r in original}
    for seed in sorted({r['seed'] for r in original}):
        a,b=grouped[seed,MODELS[0]],grouped[seed,MODELS[1]]
        output.append(f"| {seed} | True / False | {a.get('accepted')} / {a.get('region90_covered')} | {b.get('accepted')} / {b.get('region90_covered')} | {b.get('mean_error_m',float('nan')):.1f} / {b.get('map_error_m',float('nan')):.1f} |")
    output+=['', '## Separate development diagnostics', '',
        'These controls use inspected development seed7100000 only and do not select the candidate or contribute independent final worlds. [Auxiliary declaration](ENGINE_V06_AUXILIARY.md).', '',
        '| Control | Integral | Parent-mass TV distance to uniform fine | Mean-position distance to uniform fine (m) |',
        '|---|---|---:|---:|']
    for name in ['observed_development_nominal','constructed_noiseless_known_weather']:
        for d in read(BASE/'convergence'/f'{name}.json'):
            if 'total_variation_to_uniform_fine' in d:output.append(f"| {name} | {d['mode']} | {d['total_variation_to_uniform_fine']:.6f} | {d['mean_distance_to_uniform_fine_m']:.3f} |")
    output+=['', 'The fine grid is another finite integral, not physical truth. Closer numerical agreement does not guarantee a smaller true-source point error. A projection-direction error invalidated the first constructed-control preflight; its raw files/source are retained under convergence-preflight with an explicit exclusion marker. The corrected control uses the inverse transformation. No production code or final inputs changed.', '',
        '| Development condition | Common-mode prior | Extra direction SD | Mean source error (m) | Region area fraction | Covers truth |',
        '|---|---:|---:|---:|---:|---|']
    for d in lines(BASE/'sensitivity/results.jsonl'):
        output.append(f"| {d['family']} | {d['probability']:.2f} | {d['extra_direction_sd_deg']:.0f}° | {d['mean_error_m']:.1f} | {d['region90_area_fraction']:.3f} | {d['region90_covered']} |")
    output+=['', 'The hidden-common-bias result depends strongly on the uncalibrated prior. Acceptance is not assessed in these diagnostic fits because predictive refits were disabled. Separately labelled correct-weather oracles are evaluator-only diagnoses, not deployed corrections or field calibration. Baseline0.5 mean errors retain its historical cell-center estimator; candidate0.6 integrates spatial-node positions. Both modes are cell-based finite decisions.', '']
    output+=['','## Engineering, runtime and provenance' ,'',
        'The source archive/freeze, calibration, all original regressions and every final shard must match before this report is generated. Initial non-frozen development/prototype timing, source drift and the zero-prior test-adapter mismatch are retained. Unused standard-library imports in frozen evaluation helpers were retained for byte identity; production/tests and non-frozen reporting helpers pass their recorded static checks. The final candidate does not branch on scenario names, IDs or evaluator truth. All final seeds are now inspected and cannot be reused for future model selection.','',
        'The separate engineering artifacts repeat701,017 numerical checks,900 placement checks and5,000 seeded CSV cases plus four API overload rounds. These use the existing fixed batteries; they are not that many new independent observations. Acknowledged writes, malformed-input refusals and recovery are checked explicitly. Exact current test/build/browser logs and bounded isolated resource probes are retained alongside the report. Runtime in final rows includes four-worker contention and, for scheduled cases, prediction scoring; it is not an isolated latency benchmark.','',
        'Measured tracer validation remains unperformed. Official primary data access was previously denied by the proxy, and the inspected secondary Prairie Grass workbook lacks verified provenance/units/meteorology compatibility. No synthetic outcome removes those blockers. Unknown source count, wind fields/clock errors, sensor error and a source outside the declared rectangle can still defeat this restricted steady-source model. See the failure rows and actual acceptance/coverage denominators before making an operational decision.','']
    report=ROOT/'docs/ENGINE_V06_RESULTS.md';report.write_text('\n'.join(output))
    write(BASE/'report-manifest.json',{'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'artifacts':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [report,BASE/'summary.json']}})
    print(json.dumps({'source_attempts':len(rows),'planning_fits':len(plans),'targets':{k:v for k,v in summary.items() if k.endswith('_pass') or k.endswith('_errors')}},indent=2))

if __name__=='__main__':main()
