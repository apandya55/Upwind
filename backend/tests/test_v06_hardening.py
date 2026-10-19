"""Independent bounded-memory GLS and predictive allocation regressions."""
import numpy as np
import pytest
from scipy.linalg import solve_triangular
from scipy.optimize import lsq_linear
from upwind.identifiability import whiten_grouped_profile, whiten_profile
from upwind.inference import fit
from test_inference_math import small_study

@pytest.mark.parametrize('n,groups',[(7,3),(32,6),(96,16),(512,40)])
def test_grouped_profile_matches_dense_and_constrained_gls(n,groups):
    rng=np.random.default_rng(8600+n)
    index=np.arange(n)%groups
    g=rng.normal(size=(groups,29));y=rng.normal(size=n)
    a=rng.normal(size=(n,3));cov=np.eye(n)+a@a.T/3
    x=np.column_stack([np.ones(n),np.linspace(-1,1,n)])
    actual=whiten_grouped_profile(y,g,cov,x,index,block_columns=7)
    dense=whiten_profile(y,g[index],cov,x)
    np.testing.assert_allclose(actual['loss'],dense['loss'],rtol=1e-11,atol=1e-11)
    np.testing.assert_allclose(actual['strength'],dense['strength'],rtol=1e-10,atol=1e-11)
    chol=np.linalg.cholesky(cov)
    yw=solve_triangular(chol,y,lower=True)
    for j in [0,13,28]:
        design=solve_triangular(chol,np.column_stack([g[index,j],x]),lower=True)
        oracle=lsq_linear(design,yw,bounds=([0,-np.inf,-np.inf],np.inf),tol=1e-12)
        assert actual['loss'][j]==pytest.approx(np.sum((design@oracle.x-yw)**2),rel=1e-10,abs=1e-10)

def test_grouped_profile_null_rank_and_chunk_invariance():
    rng=np.random.default_rng(8610);index=np.arange(21)%3
    g=np.column_stack([np.ones(3),rng.normal(size=(3,10))]);x=np.ones((21,2))
    args=(rng.normal(size=21),g,np.eye(21),x,index)
    a=whiten_grouped_profile(*args,block_columns=1)
    b=whiten_grouped_profile(*args,block_columns=8)
    assert a['nuisance_rank']==1 and a['strength'][0]==0
    assert a['loss'][0]==pytest.approx(a['background_loss'])
    np.testing.assert_allclose(a['loss'],b['loss'],atol=1e-12)

@pytest.mark.parametrize('method',['prediction_moments','predictive_draws','predictive_log_density'])
def test_large_prediction_target_refuses_before_covariance_allocation(method):
    inv=small_study();f=fit(inv,diagnostics=False)
    points=[inv.measurements[0]]*8000
    with pytest.raises(ValueError,match='Predictive target covariance exceeds numerical workload'):
        if method=='predictive_log_density':f[method](np.zeros(8000),points)
        else:f[method](points)
