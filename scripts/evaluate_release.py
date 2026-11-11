"""Describe NC out-of-fold accuracy with station-cluster bootstrap intervals."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from export_and_benchmark import scores
from evaluate_national_v2 import haversine

ROOT = Path(__file__).resolve().parents[1]

def main():
    frame = pd.read_parquet(ROOT / 'release/upwind_nc_air_quality.parquet')
    predictions = pd.read_csv(ROOT / 'release/spatial_predictions.csv')
    identities = predictions[['id','fold']].drop_duplicates()
    if identities.id.duplicated().any():
        raise ValueError('Station appears in multiple folds')
    frame = frame.merge(identities, on='id', validate='many_to_one')
    distances = []
    baseline = []
    for row in predictions.itertuples():
        train = frame[(frame.year == row.year) & (frame.fold != row.fold)]
        target = frame[(frame.id == row.id) & (frame.year == row.year)].iloc[0]
        distances.append(float(haversine(np.array([[target.latitude,target.longitude]]), train[['latitude','longitude']].to_numpy()).min()))
        baseline.append(float(train.pm25_ug_m3.mean()))
    predictions['nearest_training_km'] = distances
    mean = predictions[predictions.method == 'nearest_monitor'].copy()
    mean['predicted'] = np.array(baseline)[predictions.method == 'nearest_monitor']
    mean['method'] = 'training_mean'
    predictions = pd.concat([predictions, mean], ignore_index=True)
    predictions['distance_band'] = pd.cut(predictions.nearest_training_km, [0,25,50,100,float('inf')], include_lowest=True).astype(str)
    predictions['region'] = predictions.id.str.slice(0,6) # AQS state-county code
    output = {'scope':'NC regional exploratory evaluation; not national validation',
              'uncertainty':'95% percentile intervals, 1000 station-cluster bootstrap draws, seed 20261114. All years of sampled stations move together. Neighboring stations may remain correlated.', 'methods':{}}
    for method, group in predictions.groupby('method'):
        rng = np.random.default_rng(20261114)
        ids = sorted(group.id.unique())
        clusters = {station: group[group.id == station] for station in ids}
        draws = []
        for _ in range(1000):
            sample = pd.concat([clusters[s] for s in rng.choice(ids,len(ids),replace=True)])
            draws.append(scores(sample.observed, sample.predicted))
        output['methods'][method] = {'overall':scores(group.observed,group.predicted),
            'cluster_intervals':{metric: np.quantile([r[metric] for r in draws if r[metric] is not None],[.025,.975]).tolist() for metric in ['MAE','RMSE','R2']},
            **{dimension:{str(k):scores(v.observed,v.predicted) for k,v in group.groupby(dimension)} for dimension in ['year','region','distance_band']}}
    (ROOT/'release/evaluation.json').write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    predictions.to_csv(ROOT/'release/evaluation_predictions.csv',index=False)
    lines = ['\n## Extended regional evaluation', '', output['uncertainty'], '',
             '| Method | MAE | RMSE | R² | MAE 95% interval |', '|---|---:|---:|---:|---|']
    for method, result in output['methods'].items():
        m = result['overall']
        lo, hi = result['cluster_intervals']['MAE']
        lines.append(f"| {method} | {m['MAE']:.6f} | {m['RMSE']:.6f} | {m['R2']:.6f} | {lo:.6f}–{hi:.6f} |")
    lines += ['', 'Full county (AQS state-county code), year, and nearest-training-distance breakdowns and intervals for all metrics: `release/evaluation.json`. Predictions including the training-mean baseline: `release/evaluation_predictions.csv`. These exploratory regional scores do not replace the national deployed-model evaluation.']
    path = ROOT/'BENCHMARKS.md'
    base = path.read_text().split('\n## Extended regional evaluation')[0]
    path.write_text(base+'\n'.join(lines)+'\n')

if __name__ == '__main__':
    main()
