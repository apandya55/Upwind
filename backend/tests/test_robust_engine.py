"""Independent integration, decision-loss and migration contracts for 0.6."""
import json
import numpy as np
import pytest
from scipy.stats import multivariate_normal
from upwind.inference import fit, region, CONFIG
from upwind.source_grid import subdivide, location_summary
from upwind.weather_evidence import joint_weather_grid
from upwind.models import migrate_analysis
from upwind.numerics import projector
from test_weather_bias import comparison_case
from test_inference_math import small_study, projected_points, covariance_oracle, unit_plume_oracle, integrated_strength


def test_refinement_preserves_area_and_does_not_drop_low_mass_cells():
    cells=np.array([[0.,0.,2.,2.],[2.,0.,4.,2.],[0.,2.,2.,4.]])
    refined,count=subdivide(cells,np.array([.95,.04,.01]),limit=1)
    assert count==1 and len(refined)==6
    area=np.prod(refined[:,2:]-refined[:,:2],axis=1)
    assert area.sum()==pytest.approx(12.)
    assert any(np.array_equal(c,cells[2]) for c in refined)
    centers=(refined[:,:2]+refined[:,2:])/2
    assert np.all(((centers[:,None]>refined[None,:,:2])&(centers[:,None]<refined[None,:,2:])).all(axis=2).sum(axis=1)==1)
    # An independent polynomial integral is preserved exactly by area-midpoints.
    assert np.sum(area*centers[:,0])==pytest.approx(20.)


def test_density_region_does_not_prefer_large_cells_over_high_density():
    cells=np.array([[0.,0.,1.,1.],[1.,0.,11.,1.]])
    result=region(dict(cells_xy=cells,cell_weights=np.array([.91,.09]),projection=projector(0,0),continuous=True,excluded_domain_area_m2=0))
    assert result['area_m2']==pytest.approx(1.)
    # Reverse mass ordering relative to density: small cell first, then large.
    result=region(dict(cells_xy=cells,cell_weights=np.array([.2,.8]),projection=projector(0,0),continuous=True,excluded_domain_area_m2=0))
    assert result['cells'][0]['weight']==pytest.approx(.2)


def test_posterior_mean_minimizes_expected_squared_loss_and_preserves_covariance():
    points=np.array([[0.,0.],[20.,10.],[100.,-30.]])
    w=np.array([.7,.2,.1]);cells=np.column_stack((points-1,points+1));tr=projector(0,0)
    result=location_summary(points,w,cells,w,(np.array([-100.,-100.]),np.array([200.,200.])),tr)
    mean=np.array(tr.transform(result['posterior_mean']['longitude'],result['posterior_mean']['latitude']))
    np.testing.assert_allclose(mean,[14.,-1.],atol=1e-7)
    loss=np.sum(w*np.sum((points-mean)**2,axis=1))
    for alternative in [points[0],points[-1],mean+np.array([13.,-5.])]:
        difference=np.sum(w*np.sum((points-alternative)**2,axis=1))-loss
        assert difference==pytest.approx(np.sum((alternative-mean)**2),abs=1e-5)
    assert result['spatial_rms_m']**2==pytest.approx(loss)


def test_domain_strip_is_fixed_in_geography_and_does_not_certify_completeness():
    points=np.array([[1.,50.],[50.,50.]])
    cells=np.array([[0.,49.,2.,51.],[49.,49.,51.,51.]])
    result=location_summary(points,np.array([.7,.3]),cells,np.array([.7,.3]),(np.zeros(2),np.full(2,100.)),projector(0,0))
    assert result['edge_mass']==pytest.approx(.7) and result['domain_limited']
    assert 'cannot verify domain completeness' in result['meaning']


def test_joint_weather_mixture_keeps_speed_direction_dependence_and_prior_mass():
    inv=comparison_case();tr=projector(0,0);primary=[w for w in inv.weather if w.role=='primary']
    a,s,c,summary=joint_weather_grid(inv,tr,primary)
    assert c.shape==(2,len(a),len(s))
    np.testing.assert_allclose(c.sum(axis=(1,2)),[.75,.25],atol=1e-14)
    joint=c.sum(axis=0)
    assert not np.allclose(joint,np.outer(joint.sum(axis=1),joint.sum(axis=0)),atol=1e-7)
    assert np.sum(joint[abs(a-summary['direction_center_deg'])>30])>0.01
    assert summary['status']=='comparison_supplied'
    assert 'uncalibrated research assumptions' in summary['common_mode_meaning']


def test_unknown_weather_is_not_narrowed_by_nonqualifying_reference_claims():
    inv=comparison_case()
    for w in inv.weather:w.upstream_id='same-instrument'
    a,s,c,summary=joint_weather_grid(inv,projector(0,0),[w for w in inv.weather if w.role=='primary'])
    assert c.shape[0]==1 and c.sum()==pytest.approx(1.)
    assert summary['status']=='unverified' and summary['total_direction_sd_deg']>=20
    assert summary['common_mode_prior_probability']==0


def test_joint_reference_source_evidence_matches_independent_strength_quadrature():
    inv=small_study()
    # Discrete anchors allow a direct scalar source×angle×speed reference, without
    # relying on the production spatial integrator or its analytic strength step.
    for w in inv.weather:w.upstream_id='A'
    inv.weather += [w.model_copy(update=dict(role='reference',source_id='B',upstream_id='B',direction_systematic_sd_deg=2.,speed_systematic_fraction=.03,comparison_provenance='Constructed test',wind_from_deg=265.)) for w in inv.weather]
    inv.settings.met_direction_sd_deg=3.
    f=fit(inv,diagnostics=False,weather_step_deg=30.)
    rows=f['rows'];x=projected_points(f['projection'],rows);t=np.array([-120.,0.,120.]);ids=[r.sensor_id for r in rows]
    cov=covariance_oracle(x,t,ids,x,t,ids,inv.settings.noise_ug_m3)+np.diag([r.uncertainty_ug_m3**2 for r in rows])
    y=np.array([r.pm25_ug_m3 for r in rows]);bg=CONFIG['background_mean_ug_m3']
    masses=[(1-CONFIG['source_prior'])*multivariate_normal.pdf(y,mean=np.full(len(y),bg),cov=cov)]
    for source in f['source_xy']:
        for i,angle in enumerate(f['weather_grid']['offsets']):
            for j,speed in enumerate(f['weather_grid']['speed_scales']):
                evidence,_,_=integrated_strength(y,bg,cov,unit_plume_oracle(x,source,2*speed,270+angle))
                masses.append(evidence*CONFIG['source_prior']/len(f['source_xy'])*f['weather_grid']['joint_prior'][i,j])
    masses=np.array(masses);masses=masses[masses>0];masses/=masses.sum()
    np.testing.assert_allclose(f['weights'],masses,rtol=5e-9,atol=1e-13)
    assert 0<=f['meteorology']['common_mode_posterior_probability']<=1
    # Exact predictive moments remain the law of total covariance of the same
    # joint mixture; this catches pruning alternatives from the planner path.
    target=[inv.source_locations[0].model_copy(update={'latitude':inv.measurements[0].latitude,'longitude':inv.measurements[0].longitude})]
    means,covs=f['predictive'](target)
    mean,total=f['prediction_moments'](target)
    expected=f['weights']@means
    expected_var=np.einsum('k,kij->ij',f['weights'],covs)+(means-expected).T@(f['weights'][:,None]*(means-expected))
    np.testing.assert_allclose(mean,expected)
    np.testing.assert_allclose(total,expected_var,rtol=1e-12)


def test_old_05_result_is_archived_losslessly_and_migration_is_idempotent():
    inv=small_study();original={'model_version':'plume-weather-0.5.0','metadata':{'preserve':'raw'},'plans':[]}
    inv.result=json.loads(json.dumps(original));before=[w.model_dump() for w in inv.weather]
    migrate_analysis(inv);migrate_analysis(inv)
    assert inv.result is None and inv.archived_results==[original]
    assert len(inv.compatibility_notes)==1
    assert [w.model_dump() for w in inv.weather]==before


@pytest.mark.parametrize('invalid',[-1.,float('nan'),float('inf')])
def test_refinement_refuses_invalid_mass(invalid):
    with pytest.raises(ValueError):subdivide(np.array([[0.,0.,1.,1.]]),np.array([invalid]))


@pytest.mark.parametrize("n", [2, 7, 32, 96, 512])
def test_grouped_transport_preserves_full_correlated_gaussian_likelihood(n):
    from upwind.gaussian_design import grouped_design
    from scipy.linalg import cho_solve
    rng = np.random.default_rng(90606+n)
    m=max(1,n//4)
    index=np.r_[np.arange(m),rng.integers(m,size=n-m)]
    a=rng.normal(size=(n,n));cov=a@a.T+np.eye(n)*.2
    chol=np.linalg.cholesky(cov)
    signatures=rng.normal(size=(m,45));residual=rng.normal(size=n)
    norm,dot,inverse_basis=grouped_design(chol,index,residual,signatures)
    expanded=signatures[index]
    np.testing.assert_allclose(norm,np.sum(expanded*cho_solve((chol,True),expanded),axis=0),rtol=1e-11,atol=1e-11)
    np.testing.assert_allclose(dot,expanded.T@cho_solve((chol,True),residual),rtol=1e-11,atol=1e-11)
    np.testing.assert_allclose(inverse_basis@signatures,cho_solve((chol,True),expanded),rtol=1e-11,atol=1e-11)
