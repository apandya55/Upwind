from pathlib import Path
import json
import hashlib
import pytest

ROOT = Path(__file__).resolve().parents[2]

def test_release_artifacts():
    pq = pytest.importorskip('pyarrow.parquet')
    pdf = pytest.importorskip('pypdf')
    path = ROOT/'release/upwind_nc_air_quality.parquet'
    frame = pq.read_table(path).to_pandas()
    assert not frame.duplicated(['id','year']).any()
    assert len(frame) == 160 and frame.id.nunique() == 23
    assert pq.ParquetFile(path).metadata.row_group(0).column(0).compression == 'ZSTD'
    assert len(pdf.PdfReader(ROOT/'reports/nc-school-corridors-2026.pdf').pages) == 3
    for suffix in ['html','pdf']:
        name = f'nc-school-corridors-2026.{suffix}'
        assert (ROOT/'reports'/name).read_bytes() == (ROOT/'frontend/public/reports'/name).read_bytes()
    for name, checksum in json.loads((ROOT/'reports/manifest.json').read_text()).items():
        assert hashlib.sha256((ROOT/'reports'/name).read_bytes()).hexdigest() == checksum


def test_evaluation_integrity():
    pd = pytest.importorskip('pandas')
    predictions = pd.read_csv(ROOT/'release/evaluation_predictions.csv')
    assert not predictions.duplicated(['id','year','method']).any()
    assert predictions.groupby('id').fold.nunique().max() == 1
    assert predictions.predicted.notna().all()
    assert predictions.nearest_training_km.gt(0).all()
    report = json.loads((ROOT/'release/evaluation.json').read_text())
    assert set(report['methods']) == {'training_mean','nearest_monitor','idw_k4_p2','gaussian_kernel_ridge_150km'}
    assert all(v['overall']['n'] == 160 for v in report['methods'].values())
