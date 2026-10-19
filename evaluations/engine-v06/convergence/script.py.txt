"""Development-only geographic quadrature convergence, not field validation."""
import gc
import hashlib
import json
from pathlib import Path
import numpy as np
from upwind.inference import fit
from upwind.source_grid import subdivide
from upwind.validation.cases import scalar_plume
from evaluate_v06 import BASE, case, hashes, write, metrics

out=BASE/'convergence';out.mkdir(exist_ok=False)
before=hashes()
write(out/'metadata.json',{'role':'Post-freeze numerical diagnosis on inspected development seed7100000, not final accuracy evidence','source_sha256':before,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'controls':['observed_development_nominal','constructed_noiseless_known_weather'],'method':'Compare original integral, one adaptive subdivision and uniform full subdivision. No model/threshold selection.'})
(out/'script.py.txt').write_bytes(Path(__file__).read_bytes())
for control in ['observed_development_nominal','constructed_noiseless_known_weather']:
    inv,truth=case('characterized_nominal',7100000,'development')
    oracle=control.startswith('constructed')
    if oracle:
        inv.weather=[w for w in inv.weather if w.role=='primary']
        for j,w in enumerate(inv.weather):w.wind_from_deg=truth['true_angles'][j//4];w.wind_speed_m_s=truth['speed']
        inv.settings.noise_ug_m3=.5;inv.settings.met_speed_fraction=0.
        # Use the evaluator's documented local generator frame for construction.
        from upwind.validation.research.cases import transform
        frame=transform('development')
        for row in inv.measurements:
            period=next(i for i,w in enumerate(inv.study_windows) if w.start<=row.timestamp<=w.end)
            xy=frame.transform(row.longitude,row.latitude,direction="INVERSE")
            row.pm25_ug_m3=10.+scalar_plume(xy,truth['source_xy'],truth['strength'],truth['speed'],truth['true_angles'][period])
            row.uncertainty_ug_m3=.01
    write(out/f'input-{control}.json',{'investigation':inv.model_dump(),'private_evaluator_truth':truth,'constructed_known_weather_control':oracle})
    results=[];coarse_cells=None
    for name in ['coarse','adaptive','uniform_fine']:
        kwargs={'diagnostics':False,'wind_uncertainty':not oracle}
        if name=='coarse':kwargs['_adaptive']=False
        if name=='uniform_fine':
            fine,_=subdivide(coarse_cells,np.ones(len(coarse_cells))/len(coarse_cells),target=1.,limit=len(coarse_cells))
            kwargs.update(_cells=fine,_adaptive=False)
        try:
            f=fit(inv,**kwargs)
            if name=='coarse':coarse_cells=f['cells_xy'].copy()
            cells=f['cells_xy'];centers=(cells[:,:2]+cells[:,2:])/2
            membership=np.all((centers[:,None]>coarse_cells[None,:,:2])&(centers[:,None]<coarse_cells[None,:,2:]),axis=2)
            assert np.all(membership.sum(axis=1)==1)
            mass=np.bincount(membership.argmax(axis=1),weights=f['cell_weights'],minlength=len(coarse_cells))
            p=f['location_estimate']['posterior_mean'];mean=np.array(f['projection'].transform(p['longitude'],p['latitude']))
            result=dict(mode=name,status='fitted',cells=len(cells),**metrics(f,truth,False),coarse_parent_mass=mass.tolist(),posterior_mean_xy=mean.tolist())
        except ValueError as exc:result=dict(mode=name,status='refused',reason=str(exc))
        results.append(result)
        if "f" in locals():del f
        gc.collect()
    if results[-1]['status']=='fitted':
        reference=results[-1]
        for r in results[:-1]:
            if r['status']=='fitted':
                r['total_variation_to_uniform_fine']=float(.5*np.sum(abs(np.array(r['coarse_parent_mass'])-reference['coarse_parent_mass'])))
                r['mean_distance_to_uniform_fine_m']=float(np.linalg.norm(np.array(r['posterior_mean_xy'])-reference['posterior_mean_xy']))
    write(out/f'{control}.json',results)
write(out/'completion.json',{'source_unchanged':before==hashes(),'controls':2,'scheduled_integrals':6})
