"""Isolated large-target memory boundary probe; constructed data only."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend/tests'))
from test_inference_math import small_study
from upwind.inference import fit
from upwind.models import Point

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
inv=small_study();inv.synthetic=True
for row in inv.measurements+inv.weather:row.origin='synthetic'
f=fit(inv,diagnostics=False)
points=[Point(latitude=inv.measurements[0].latitude,longitude=inv.measurements[0].longitude)]*8000
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
t=time.perf_counter()
try:
 f['prediction_moments'](points);result={'outcome':'unexpectedly_allocated'}
except MemoryError as exc:result={'outcome':'memory_error','reason':str(exc)}
except ValueError as exc:result={'outcome':'explicit_refusal','reason':str(exc)}
result.update(targets=8000,address_space_mib=1024,seconds=time.perf_counter()-t,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,role='Constructed library boundary probe, no source truth or field data')
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
