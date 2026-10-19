"""Paired, append-only UW-ENGINE-2026-06 evaluator; truth is never fitted."""
import argparse
import gc
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import resource
import numpy as np
from upwind.models import Investigation, Measurement
from upwind.inference import fit, CONFIG, MODEL_VERSION
from upwind.validation import weather_bias as wb
from upwind.validation.research.cases import point, reveal
from upwind.validation.research.run import source_metrics, score_prediction
import severe_stress as stress

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'evaluations/engine-v06'
SEEDS = {'development': range(7100000,7100004), 'calibration': range(7200000,7200008), 'final': range(7300000,7300024)}
FAMILIES = stress.FAMILIES

def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')

def hashes():
    paths = list((ROOT/'backend/upwind').rglob('*.py')) + [Path(__file__), ROOT/'scripts/severe_stress.py', ROOT/'scripts/plan_v06.py', ROOT/'scripts/regress_v06.py', ROOT/'docs/ENGINE_V06_PROTOCOL.md', ROOT/'requirements.lock', ROOT/'frontend/package-lock.json']
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def baseline():
    name = '_upwind_v06_baseline'
    if name not in sys.modules:
        p = BASE/'baseline-source/backend/upwind'
        spec = importlib.util.spec_from_file_location(name,p/'__init__.py',submodule_search_locations=[str(p)])
        module = importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return [importlib.import_module(name+'.'+m) for m in ('inference','models')]

def case(family, seed, stage):
    split = {'development':'development','calibration':'calibration','final':'final'}[stage]
    rng = np.random.default_rng(seed+17_000_000)
    bands={'development':(10,700,170,[220,255,285,315]),'calibration':(50,850,200,[210,245,295,325]),'final':(15,950,235,[198,238,302,342])}
    lo,hi,y,angles=bands[stage]
    layout=np.column_stack((rng.uniform(lo,hi,6),rng.uniform(-y,y,6)))
    angles=np.array(angles)+rng.uniform(-8,8,4)
    original_layout,original_angles=wb.LAYOUTS[split],wb.ANGLES[split]
    try:
        wb.LAYOUTS[split],wb.ANGLES[split]=layout.tolist(),angles.tolist()
        inv,truth=wb.world('characterized_nominal' if family in stress.EXTRA else family,seed,split)
    finally:
        wb.LAYOUTS[split],wb.ANGLES[split]=original_layout,original_angles
    # Reuse the declared challenge mutations, preserving their raw provenance.
    if family in stress.EXTRA:
        mutated,record=stress.case(family,seed)
        mutation=record['mutation']
        if family=='sensor_dropout':
            inv.measurements=[m for m in inv.measurements if m.sensor_id not in mutation['removed_sensor_ids']]
        elif family=='sensor_bias':
            for m in inv.measurements:
                if m.sensor_id==mutation['sensor']:m.pm25_ug_m3+=mutation['additive_bias_ug_m3']
        elif family=='shared_reference_bias':
            for w in inv.weather:w.wind_from_deg=float((w.wind_from_deg+mutation['hidden_common_bias_deg'])%360)
        elif family=='source_outside_domain':
            from upwind.models import Point
            inv.source_locations=[Point(**point((x,y),split)) for x in (-680.,-590.,-500.) for y in (-220.,0.,220.)]
        elif family=='extreme_readings':
            for m in inv.measurements:
                if m.sensor_id=='M00':m.pm25_ug_m3=650.
        elif family=='shared_lineage':
            for w in inv.weather:
                if w.role=='reference':w.upstream_id='instrument-A'
                else:w.wind_from_deg=float((w.wind_from_deg+mutation['primary_shift_deg'])%360)
        truth['mutation']=mutation
    truth.update(family=family,protocol='UW-ENGINE-2026-06',layout=layout.tolist(),angles=angles.tolist())
    inv.name=f'SYNTHETIC v06 {stage} {family} {seed}'
    return Investigation.model_validate(inv.model_dump()),truth

def metrics(f, truth, old):
    return source_metrics(f,truth)

def targets(truth):
    return [Measurement(sensor_id=f'unseen-{j}',timestamp=truth['last_timestamp'],origin='synthetic',pm25_ug_m3=float(v),uncertainty_ug_m3=float(s),**point(xy,truth['split'])) for j,(xy,v,s) in enumerate(zip(truth['target_xy'],truth['target_outcomes'],truth['future_sigma'][12:]))]

def evaluate(inv, truth, old, predict):
    t=time.perf_counter();row={'family':truth['family'],'seed':truth['seed'],'model':'plume-weather-0.5.0' if old else MODEL_VERSION,'prediction_scheduled':predict}
    f=None
    try:
        if old:
            inference,models=baseline();f=inference.fit(models.Investigation.model_validate(inv.model_dump()),diagnostics=True)
        else:f=fit(inv,diagnostics=True)
        row.update(status='fitted',**metrics(f,truth,old),warning=bool(f['diagnostics']['predictive_warning']),weather_warning=bool(f['meteorology']['weather_warning']),diagnostics=f['diagnostics'],meteorology=f['meteorology'],rows_used=f['rows_used'],scenario_count=f['scenario_count'])
        row['accepted']=wb.accepted(row) and (old or not f['location_estimate']['domain_limited'])
        row['numeric_ok']=bool(np.isfinite(f['weights']).all() and np.all(f['weights']>=0) and abs(f['weights'].sum()-1)<1e-9 and abs(f['cell_weights'].sum()-1)<1e-9)
        if not old:row.update(location_estimate=f['location_estimate'],quadrature=f['quadrature_diagnostics'])
        if predict:
            reveal(truth)
            row['prediction']={'status':'scored',**score_prediction(f,targets(truth),truth['target_outcomes'])}
    except ValueError as exc:row.update(status='refused',reason=str(exc))
    except Exception as exc:row.update(status='crash',reason=f'{type(exc).__name__}: {exc}')
    row['wall_ms']=1000*(time.perf_counter()-t)
    row['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    return row

def freeze(out):
    if (out/'freeze.json').exists():
        raise FileExistsError('A source freeze already exists; choose a new evidence directory')
    snapshot=hashes();write(out/'freeze.json',{'protocol':'UW-ENGINE-2026-06','model':MODEL_VERSION,'config':CONFIG,'sha256':snapshot,'seeds':{k:list(v) for k,v in SEEDS.items()},'families':FAMILIES})
    for name in snapshot:
        p=out/'frozen-source'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)

def run(out,stage,shard,families=None):
    before=hashes();frozen=json.loads((out/'freeze.json').read_text()) if stage=='final' else None
    if frozen:assert frozen['sha256']==before and frozen['config']==CONFIG
    folder=out/f'{stage}-{shard}';folder.mkdir(parents=True,exist_ok=False)
    families=FAMILIES if families is None else families
    seeds=list(SEEDS[stage])[shard::4]
    write(folder/'metadata.json',{'sha256_before':before,'seeds':seeds,'families':families,'stage':stage,'config':CONFIG})
    t=time.perf_counter()
    for seed in seeds:
        for family in families:
            inv,truth=case(family,seed,stage)
            write(folder/f'input-{family}-{seed}.json',{'investigation':inv.model_dump(),'private_evaluator_truth':truth})
            for old in (True,False):
                row=evaluate(inv,truth,old,predict=(seed<list(SEEDS[stage])[0]+4))
                with (folder/'results.jsonl').open('a') as file:file.write(json.dumps(row,allow_nan=False)+'\n')
                print(stage,seed,family,row['model'],row['status'],row.get('accepted'),round(row['wall_ms']/1000,2),flush=True)
                del row;gc.collect()
    write(folder/'completion.json',{'source_unchanged':before==hashes(),'sha256_after':hashes(),'seconds':time.perf_counter()-t,'config_unchanged':not frozen or frozen['config']==CONFIG})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['freeze','development','calibration','final']);parser.add_argument('--out',type=Path,default=BASE);parser.add_argument('--shard',type=int,choices=range(4),default=0);parser.add_argument('--families',nargs='+',choices=FAMILIES)
    args=parser.parse_args()
    if args.mode=='freeze':freeze(args.out)
    else:run(args.out,args.mode,args.shard,args.families)
