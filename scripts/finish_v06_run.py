"""Wait for declared evidence, then execute remaining isolated checks sequentially."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'evaluations/engine-v06'
start=time.monotonic()
while True:
    attempts=sum(len(p.read_text().splitlines()) for p in BASE.glob('final-*/results.jsonl'))
    planning=sum(len(p.read_text().splitlines()) for p in BASE.glob('planning-*/results.jsonl'))
    complete=all((BASE/f'{phase}-{i}/completion.json').exists() for phase in ['final','planning','calibration','original18'] for i in range(4)) and (BASE/'original04-reproduction/summary.json').exists()
    status={'final_source_attempts':attempts,'expected_final_source_attempts':960,'planning_attempts':planning,'expected_planning_attempts':48,'scientific_workers_complete':complete}
    (BASE/'run-status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    if complete:break
    if time.monotonic()-start>10800:raise TimeoutError('Declared evidence incomplete after three hours; preserve workers and inspect logs')
    time.sleep(45)
commands=[
 ('passive-controls',[sys.executable,'scripts/passive_controls_v06.py']),
 ('resources',[sys.executable,'-m','upwind.validation.weather_aux','resources','--out',str(BASE/'resources')]),
 ('release-checks',[sys.executable,'scripts/check_v06_release.py']),
 ('report',[sys.executable,'scripts/report_v06.py']),
 ('plot',[sys.executable,'scripts/plot_v06.py']),
]
for name,cmd in commands:
    print('Starting',name,flush=True)
    with (BASE/f'postrun-{name}.log').open('x') as log:
        result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MPLCONFIGDIR':str(ROOT/'.local/mplconfig')})
    print('Completed',name,'exit',result.returncode,flush=True)
    if result.returncode:raise SystemExit(result.returncode)
print('All declared fits and post-run checks finished. Inspect figure/results, finalize docs, then run verify_v06.py.',flush=True)
