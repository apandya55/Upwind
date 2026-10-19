"""Compare ordinary inference/prediction outputs to archived scientific source."""
import importlib
import importlib.util
import sys
import numpy as np
from evaluate_v06 import BASE,ROOT,write
from hardening_v06 import validate_source
sys.path.insert(0,str(ROOT/'backend/tests'))
from test_inference_math import small_study
from upwind.inference import fit
before=validate_source()
name='_upwind_v06_frozen'
p=BASE/'frozen-source/backend/upwind'
spec=importlib.util.spec_from_file_location(name,p/'__init__.py',submodule_search_locations=[str(p)])
module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
old=importlib.import_module(name+'.inference');models=importlib.import_module(name+'.models')
cases=[]
# Two inspected constructed cases, no new scientific holdout or model selection.
for delta in [0.,1.25]:
 inv=small_study()
 for row in inv.measurements:row.pm25_ug_m3+=delta
 a=old.fit(models.Investigation.model_validate(inv.model_dump()),diagnostics=False)
 b=fit(inv,diagnostics=False)
 checked=[]
 for key in ['weights','cell_weights','source_xy','cells_xy']:
  np.testing.assert_array_equal(a[key],b[key]);checked.append(key)
 pts=inv.measurements[:2]
 for method in ['prediction_moments','predictive_draws','predictive_log_density']:
  if method=='predictive_log_density':x=a[method]([10.,11.],pts);y=b[method]([10.,11.],pts)
  elif method=='predictive_draws':x=a[method](pts,samples=16,seed=34);y=b[method](pts,samples=16,seed=34)
  else:x=a[method](pts);y=b[method](pts)
  for left,right in zip(x,y):np.testing.assert_array_equal(left,right)
  checked.append(method)
 cases.append({'constructed_concentration_offset':delta,'exact_array_equal':checked})
assert before==validate_source()
write(BASE/'hardening-equivalence.json',{'passed':True,'source':before,'cases':cases,'scope':'Exact arrays on two inspected small constructed cases; diagnostic GLS independently checked by pytest. Not a new accuracy evaluation.'})
print('Frozen/current posterior and ordinary predictions exactly equal on two constructed cases')
