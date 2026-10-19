"""Protect evaluator separation and scientific reporting denominators."""
import copy
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from evaluate_v06 import case, SEEDS
from report_v06 import summarize, paired, MODELS
from upwind.validation import weather_bias as wb


def test_new_generator_restores_layout_tables_even_on_failure(monkeypatch):
    layouts,angles=copy.deepcopy(wb.LAYOUTS),copy.deepcopy(wb.ANGLES)
    def fail(*args,**kwargs):raise RuntimeError('constructed generator failure')
    monkeypatch.setattr(wb,'world',fail)
    with pytest.raises(RuntimeError,match='constructed generator failure'):
        case('characterized_nominal',7100000,'development')
    assert wb.LAYOUTS==layouts and wb.ANGLES==angles


def test_fresh_split_ranges_are_disjoint_and_truth_is_separate_from_input():
    parts=[set(v) for v in SEEDS.values()]
    assert all(not a&b for i,a in enumerate(parts) for b in parts[i+1:])
    assert not set.union(*parts)&set(range(6100000,6100048))
    inv,truth=case('characterized_nominal',7100000,'development')
    assert truth['source_present'] and truth['seed']==7100000
    data=inv.model_dump()
    assert 'private_evaluator_truth' not in data and 'source_xy' not in data
    assert all(r['origin']=='synthetic' for r in data['measurements']+data['weather'])


def test_reporting_keeps_abstentions_in_attempt_denominator():
    def row(accepted,covered):
        return dict(status='fitted',source_present=True,accepted=accepted,region90_covered=covered,region90_area_fraction=.2,source_brier=.01,map_error_m=30.,mean_error_m=20.,wall_ms=100.,numeric_ok=True)
    records=[row(True,False),row(True,True),row(False,True),dict(status='refused',reason='weather',wall_ms=10.)]
    report=summarize(records)
    assert report['accepted']['k']==2 and report['accepted']['n']==4
    assert report['accepted_wrong']['k']==1 and report['accepted_wrong']['n']==2
    assert report['accepted_wrong_all']['k']==1 and report['accepted_wrong_all']['n']==4
    assert report['coverage']['k']==2 and report['coverage']['n']==3
    assert report['refusals']==1 and report['crashes']==0


def test_paired_intervals_resample_seed_blocks_not_correlated_conditions():
    records=[]
    for seed,families,difference in [(0,['a','b'],100.),(1,['a'],0.)]:
        for family in families:
            records.extend([dict(model=MODELS[0],seed=seed,family=family,status='fitted',map_error_m=10.),dict(model=MODELS[1],seed=seed,family=family,status='fitted',map_error_m=10.+difference)])
    result=paired(records,'map_error_m')
    assert result['candidate_minus_baseline']==pytest.approx(50.)
    assert result['seed_blocks']==2 and result['pairs']==3
    assert result['bootstrap95']==[0.,100.]
