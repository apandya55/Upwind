from hardening_v06 import validate_source
"""Verify exact source, raw paired attempts, contracts and derived artifacts."""
import hashlib
import json
from evaluate_v06 import BASE, ROOT, FAMILIES, SEEDS, CONFIG, write
from report_v06 import MODELS, summarize

def read(path):return json.loads(path.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rows(path):return [json.loads(s) for s in path.read_text().splitlines()]

def main():
    frozen=read(BASE/'freeze.json')
    current=validate_source()
    assert CONFIG==frozen['config'],'Candidate configuration changed'
    for name,expected in frozen['sha256'].items():assert digest(BASE/'frozen-source'/name)==expected,name
    for name,expected in read(BASE/'baseline-manifest.json')['sha256'].items():assert digest(BASE/'baseline-source'/name)==expected,name
    final=[];calibration=[];original=[];planning=[];inputs=0
    for stage,destination in [('final',final),('calibration',calibration),('original18',original),('planning',planning)]:
        for i in range(4):
            folder=BASE/f'{stage}-{i}';complete=read(folder/'completion.json')
            assert complete['source_unchanged'] and complete['sha256_after']==frozen['sha256'],str(folder)
            if stage in ['final','calibration','original18']:
                metadata=read(folder/'metadata.json');assert metadata['sha256_before']==frozen['sha256'],str(folder)
            destination.extend(rows(folder/'results.jsonl'))
            if stage=='final':
                for p in folder.glob('input-*.json'):
                    data=read(p);study=data['investigation'];truth=data['private_evaluator_truth'];inputs+=1
                    assert truth['seed'] in SEEDS['final'] and truth['family'] in FAMILIES
                    assert study['synthetic'] and 'private_evaluator_truth' not in study
                    assert all(r['origin']=='synthetic' for r in study['measurements']+study['weather'])
    assert inputs==480 and len(final)==960
    assert {(r['model'],r['family'],r['seed']) for r in final}=={(m,f,s) for m in MODELS for f in FAMILIES for s in SEEDS['final']}
    assert len(calibration)==128 and len(original)==36 and len(planning)==48
    for row in planning:
        assert row['cost']<=250+1e-8 and row['equipment']<=2 and row['equipment']==len(row['site_ids'])
        path=BASE/f"planning-{row['seed']-7300000}"/f"locked-{row['family']}.json"
        assert row['locked_sha256']==digest(path)
        assert read(path)['plans'][row['method']]==row['site_ids']
    summary=read(BASE/'summary.json')
    for m in MODELS:
        actual=summarize([r for r in final if r['model']==m]);assert summary['overall'][m]==actual
        assert sum(r['model']==m and r['prediction_scheduled'] for r in final)==80
    for name in ['report-manifest.json','figure-manifest.json']:
        manifest=read(BASE/name)
        for path,expected in manifest['artifacts'].items():assert digest(ROOT/path)==expected,path
        script=ROOT/'scripts'/('report_v06.py' if name.startswith('report') else 'plot_v06.py')
        assert digest(script)==manifest['script_sha256']
    assert digest(BASE/'summary.json')==read(BASE/'figure-manifest.json')['input_sha256']
    # Historical evidence retains its own archived source, not current 0.6 bytes.
    historic=ROOT/'evaluations/severe-stress';old=read(historic/'freeze.json')
    for name,expected in old['source_hashes'].items():assert digest(historic/'source'/name)==expected,name
    for name in ['report-manifest.json','figure-manifest.json']:
        m=read(historic/name)
        for path,expected in m.get('artifacts',m).items():assert digest(ROOT/path)==expected,path
    engineering=BASE/'engineering'
    numeric=read(engineering/'numerical.json');placement=read(engineering/'placement.json');fuzz=read(engineering/'csv-fuzz.json');api=read(engineering/'api-rounds.json')
    assert numeric['failed_groups']==0 and placement['passed'] and fuzz['passed'] and all(r['passed'] for r in api)
    assert read(engineering/'completion.json')['script_sha256']==digest(ROOT/'scripts/stress_engineering.py')
    sensitivity=read(BASE/'sensitivity/completion.json');assert sensitivity['source_unchanged'] and sensitivity['configuration_restored']
    sensitivity_meta=read(BASE/'sensitivity/metadata.json');assert sensitivity_meta['script_sha256']==digest(BASE/'sensitivity/script.py.txt')==digest(ROOT/'scripts/diagnose_v06.py')
    assert len(rows(BASE/'sensitivity/results.jsonl'))==10
    convergence=read(BASE/'convergence/completion.json');assert convergence['source_unchanged'] and convergence['scheduled_integrals']==6
    assert read(BASE/'convergence/metadata.json')['script_sha256']==digest(BASE/'convergence/script.py.txt')==digest(ROOT/'scripts/converge_v06.py')
    assert read(BASE/'convergence-preflight/INVALID_CONTROL.json')['excluded_from_results']
    control_meta=read(BASE/'passive-controls/metadata.json')
    assert control_meta['script_sha256']==digest(BASE/'passive-controls/script.py.txt')==digest(ROOT/'scripts/passive_controls_v06.py')
    assert control_meta['protocol_sha256']==digest(ROOT/'docs/ENGINE_V06_PASSIVE_CONTROLS.md')
    controls=read(BASE/'passive-controls/completion.json');assert controls['control_scores']==160 and controls['scheduled_worlds']==80
    original04=read(BASE/'original04-reproduction/summary.json');assert original04['exact_reproduction'] and original04['accepted']==18 and original04['accepted_wrong']==18
    supplementary=[]
    for i in range(4):
        folder=BASE/f'observability-{i}';done=read(folder/'completion.json')
        assert done['source_unchanged'] and done['sha256_after']==frozen['sha256']
        meta=read(folder/'metadata.json')
        assert meta['script_sha256']==digest(folder/'script.py.txt')==digest(ROOT/'scripts/observability_control_v06.py')
        assert meta['protocol_sha256']==digest(ROOT/'docs/ENGINE_V06_OBSERVABILITY_CONTROL.md')
        supplementary.extend(rows(folder/'results.jsonl'))
    assert len(supplementary)==64
    observed=read(BASE/'observability-summary.json')
    for family in ['near_nominal','near_shared_bias']:
        for model in MODELS:
            assert observed[family][model]==summarize([r for r in supplementary if r['family']==family and r['model']==model])
    for name,expected in read(BASE/'hardening-validation-manifest.json')['sha256'].items():
        assert digest(ROOT/name)==expected,name
    assert read(BASE/'hardening-equivalence.json')['passed']
    assert read(BASE/'prediction-capacity-before.json')['outcome']=='memory_error'
    assert read(BASE/'prediction-capacity-after.json')['outcome']=='explicit_refusal'
    checks=read(BASE/'release-checks.json');assert checks['source_before']==checks['source_after']==current
    assert checks['config_unchanged'] and all(v==0 for v in checks['exit_codes'].values())
    assert '209 passed' in (BASE/'pytest-final.log').read_text()
    assert '8 passed' in (BASE/'playwright-final.log').read_text()
    assert 'built in' in (BASE/'frontend-build-final.log').read_text()
    resources=read(BASE/'resources/completion.json')
    for name,expected in resources['source_hashes_after'].items():
        assert current.get(name,old['source_hashes'].get(name))==expected,name
        assert digest(ROOT/name)==expected,name
    resource_rows=read(BASE/'resources/results.json');assert len(resource_rows)==5
    # Resource ceilings are measured outcomes, including refusals/failures/timeouts.
    # They are never silently converted to passing fits.
    result={'integrity_passed':True,'frozen_paths':len(frozen['sha256']),'paired_condition_worlds':inputs,'final_source_attempts':len(final),'calibration_attempts':len(calibration),'original_regression_attempts':len(original),'downstream_planning_attempts':len(planning),'inference_crashes':sum(r['status']=='crash' for r in final),'numeric_failures':sum(r.get('numeric_ok') is False for r in final),'unexpected_refusals':sum(r['status']=='refused' and r['family'] not in ['distant_station','variable_weather'] for r in final),'backend_tests':209,'browser_workflows':8,'numerical_checks':numeric['checks'],'placement_checks':placement['checks'],'csv_cases':fuzz['cases'],'resources':resource_rows,'nominal_map_50m_pass':summary['nominal_50m_map_target_pass'],'nominal_mean_50m_pass':summary['nominal_50m_mean_target_pass'],'common_bias_fewer_accepted_errors':summary['common_bias_fewer_accepted_errors'],'historical_severe_source_intact':True,'field_validation_performed':False}
    write(BASE/'verification.json',result)
    files={str(p.relative_to(ROOT)):digest(p) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name!='artifact-manifest.json' and '__pycache__' not in p.parts}
    write(BASE/'artifact-manifest.json',{'meaning':'Synthetic experiment files and source snapshots only; raw input truth is evaluator-private, not inference input','sha256':files})
    print(json.dumps({k:v for k,v in result.items() if k!='resources'},indent=2))

if __name__=='__main__':main()
