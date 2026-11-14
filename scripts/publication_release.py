#!/usr/bin/env python3
"""Validate and package the annual evidence release. Never publish remotely."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def run(*command):
    subprocess.run(command, cwd=ROOT, check=True, env={**os.environ,'PYTHONPATH':str(ROOT/'backend'),'MPLBACKEND':'Agg','SOURCE_DATE_EPOCH':'1794614400'})

def main():
    for name, expected in json.loads((ROOT/'release/inputs/manifest.json').read_text()).items():
        if hashlib.sha256((ROOT/'release/inputs'/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Input checksum mismatch: {name}')
    run(sys.executable,'scripts/export_and_benchmark.py','--monitors','release/inputs/monitors.json')
    run(sys.executable,'scripts/evaluate_release.py')
    run(sys.executable,'scripts/build_nc_report.py')
    run(sys.executable,'-m','pytest','backend/tests/test_export_and_benchmark.py','backend/tests/test_national_v2_eval.py','backend/tests/test_publication.py','-q')
    public = ROOT/'frontend/public/research'
    public.mkdir(exist_ok=True)
    import shutil
    for name in ['upwind_nc_air_quality.parquet','evaluation.json']:
        shutil.copyfile(ROOT/'release'/name,public/name)
    for name in ['BENCHMARKS.md','DATA_DICTIONARY.md']:
        shutil.copyfile(ROOT/name,public/name)
    hub = ROOT/'artifacts/huggingface'
    hub.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'publication/DATASET_CARD.md',hub/'README.md')
    for source in [ROOT/'release/upwind_nc_air_quality.parquet',ROOT/'release/evaluation.json',ROOT/'DATA_DICTIONARY.md',ROOT/'BENCHMARKS.md',ROOT/'reports/nc-school-corridors-2026.pdf']:
        shutil.copyfile(source,hub/source.name)
    (hub/'SHA256SUMS.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(hub.iterdir()) if p.name != 'SHA256SUMS.json'},indent=2)+'\n')
    files = []
    for directory in ['backend/upwind','backend/tests','scripts','frontend/src','frontend/tests','frontend/scripts','frontend/public/reports','frontend/public/research','release','reports','publication','.github/workflows']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    for pattern in ['requirements*','README.md','LICENSE','CITATION.cff','pyproject.toml','BENCHMARKS.md','DATA_DICTIONARY.md','frontend/package*.json','frontend/*.ts','frontend/*.json','frontend/index.html','vercel.json','DEPLOYMENT.md','RELEASE_READINESS.md']:
        files.extend(ROOT.glob(pattern))
    files = sorted(set(files))
    archive = ROOT/'artifacts/upwind-annual-evidence-2026.zip'
    archive.parent.mkdir(exist_ok=True)
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() if (ROOT/'.git').exists() else 'archive rebuild'
    status = subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True) if (ROOT/'.git').exists() else 'not a Git checkout'
    manifest = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in files:
            info = zipfile.ZipInfo(str(path.relative_to(ROOT)),date_time=(2026,11,14,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info,path.read_bytes())
        z.writestr('BUILD_PROVENANCE.json',json.dumps({'base_git_revision':revision,'working_tree_status':status,'note':'Archive checksums identify exact files; base revision alone does not include uncommitted changes.'},indent=2))
        z.writestr('SHA256SUMS.json',json.dumps(manifest,indent=2)+'\n')
    print(f'Publication archive: {archive}\nSHA256: {hashlib.sha256(archive.read_bytes()).hexdigest()}')

if __name__ == '__main__':
    main()
