"""Publication artifacts from completed frozen evidence; no model selection."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from evaluate_v06 import BASE, ROOT, write

summary=json.loads((BASE/'summary.json').read_text())
out=BASE/'figures';out.mkdir(exist_ok=False)
models=summary['models'];colours=['#56738b','#147d66']
fig,(ax,ecdf)=plt.subplots(1,2,figsize=(12,7),gridspec_kw={'width_ratios':[1.2,1]})
families=['characterized_nominal','shared_reference_bias','source_outside_domain','spatial_winds','correlated','independent_transport']
positions=[];labels=[]
for index,family in enumerate(families):
    for j,model in enumerate(models):
        d=summary['per_condition'][family][model];y=index*2.7+j
        correct=d['accepted']['k']-d['accepted_wrong']['k'];wrong=d['accepted_wrong']['k'];other=d['attempts']-d['accepted']['k']
        ax.barh(y,correct,color='#147d66',height=.8,label='Accepted; region contains source' if index==j==0 else None)
        ax.barh(y,wrong,left=correct,color='#bd4937',height=.8,label='Accepted wrong result' if index==j==0 else None)
        ax.barh(y,other,left=correct+wrong,color='#e0e5e9',height=.8,label='Abstained / refused' if index==j==0 else None)
        positions.append(y);labels.append(f"{family.replace('_',' ')}\n{'0.5' if j==0 else '0.6'}")
ax.set_yticks(positions,labels,fontsize=8);ax.invert_yaxis();ax.set_xlim(0,24);ax.set_xlabel('Worlds per condition (24 each)');ax.set_title('Acceptance and geographic failures');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),fontsize=8)
for model,colour in zip(models,colours):
    values=[]
    for path in sorted(BASE.glob('final-*/results.jsonl')):
        for line in path.read_text().splitlines():
            row=json.loads(line)
            if row['model']==model and row['family']=='characterized_nominal' and row['status']=='fitted':values.append(row['mean_error_m'])
    values=np.sort(values);ecdf.step(np.r_[0,values],np.r_[0,np.arange(1,len(values)+1)/len(values)],where='post',color=colour,label=model.split('-')[-1],linewidth=2)
ecdf.axvline(50,color='#bd4937',linestyle=':',label='50m aspiration');ecdf.set_xlabel('Posterior-mean location error (m)');ecdf.set_ylabel('Fraction of characterized nominal worlds');ecdf.set_ylim(0,1.02);ecdf.set_title('Location error remains distinct from coverage');ecdf.grid(alpha=.2);ecdf.legend()
fig.suptitle('UPWIND: paired synthetic comparison, 24 seed blocks',fontsize=15)
fig.text(.5,.015,'Conditional research model; these results do not establish measured field accuracy or source responsibility.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.055,1,.95))
plt.rcParams['svg.hashsalt']='upwind-engine-v06'
for suffix in ['png','svg','pdf']:fig.savefig(out/f'engine-tradeoffs.{suffix}',dpi=180)
write(BASE/'figure-manifest.json',{'input_sha256':hashlib.sha256((BASE/'summary.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'artifacts':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir())}})
print('Wrote PNG, SVG and PDF; inspect PNG before publishing.')
