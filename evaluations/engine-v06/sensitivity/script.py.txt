"""Declared development-only prior sensitivity and a labelled weather oracle."""
import copy
import hashlib
import json
from pathlib import Path
import time
from upwind.inference import fit, CONFIG
from upwind.weather_evidence import WEATHER_CONFIG
from evaluate_v06 import BASE, case, hashes, metrics, write

out=BASE/'sensitivity';out.mkdir(exist_ok=False)
original=copy.deepcopy(CONFIG);before=hashes()
write(out/'metadata.json',{'role':'Development-only sensitivity; no selection, thresholds or final-data access','source_sha256':before,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'frozen_config':original,'seed':7100000,'families':['characterized_nominal','shared_reference_bias'],'variants':[[.1,20.],[.25,20.],[.5,20.],[.25,15.],[.25,30.]],'oracle':'Separately labelled true wind only, never production inference/plans or field calibration'})
(out/'script.py.txt').write_bytes(Path(__file__).read_bytes())
for family in ['characterized_nominal','shared_reference_bias']:
    inv,truth=case(family,7100000,'development')
    for probability,sd in [[.1,20.],[.25,20.],[.5,20.],[.25,15.],[.25,30.]]:
        try:
            WEATHER_CONFIG.update(common_mode_probability=probability,common_mode_direction_sd_deg=sd)
            t=time.perf_counter();f=fit(inv,diagnostics=False)
            row=dict(family=family,probability=probability,extra_direction_sd_deg=sd,seconds=time.perf_counter()-t,**metrics(f,truth,False),meteorology=f['meteorology'],acceptance='not evaluated: predictive refits disabled')
            with (out/'results.jsonl').open('a') as file:file.write(json.dumps(row,allow_nan=False)+'\n')
        finally:
            WEATHER_CONFIG.clear();WEATHER_CONFIG.update(copy.deepcopy(original['weather_bias']))
    oracle=inv.model_copy(deep=True);oracle.weather=[w for w in oracle.weather if w.role=='primary']
    for j,w in enumerate(oracle.weather):w.wind_from_deg=truth['true_angles'][j//4];w.wind_speed_m_s=truth['speed']
    oracle.settings.met_speed_fraction=0.
    f=fit(oracle,diagnostics=False,wind_uncertainty=False)
    write(out/f'oracle-{family}.json',{'evaluator_only':True,'family':family,**metrics(f,truth,False),'warning':'True weather is evaluator knowledge; this is not an implemented measured correction.'})
write(out/'completion.json',{'source_unchanged':before==hashes(),'configuration_restored':CONFIG==original,'cases':2,'sensitivity_fits':10,'oracle_fits':2})
print('Development sensitivity completed; source unchanged and configuration restored.')
