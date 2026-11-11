#!/usr/bin/env python3
"""Regenerate all figures affected by the eligible-model tissue analysis.

Cohort wording follows the manuscript: "reference cohort" (112 samples) and
"second cfRNA cohort" (179 patients); the earlier "anchor"/"extension"
shorthand is not used in figure text. Each figure is written as PNG and PDF.
"""
import csv, json, math, os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

_savefig = Figure.savefig
def _dual_save(self, fname, *a, **kw):
    _savefig(self, fname, *a, **kw)
    p = Path(str(fname))
    if p.suffix == '.png':
        _savefig(self, p.with_suffix('.pdf'), bbox_inches='tight', pad_inches=.06)
Figure.savefig = _dual_save

DR = Path(os.environ.get(
    'MASLD_DATA_ROOT',
    os.environ.get('MASLD_LLM_ROOT', Path(__file__).resolve().parents[1]),
))
REV = Path(__file__).resolve().parents[1]
AUD = Path(os.environ.get('MASLD_ELIGIBLE_OUTPUT_DIR', REV/'results'/'eligible'))
FIG = REV/'figures'
SUP = REV/'figures_supplementary'
SUP.mkdir(exist_ok=True)
TAB = REV/'results'/'tables'
TAB.mkdir(parents=True, exist_ok=True)
NAVY, TEAL, RED, GREY = '#1d3557', '#2a9d8f', '#b5171f', '#8d99ae'
COMPACT = {'Qwen3-0.6B v3','Qwen3-0.6B v5','Qwen3-1.7B v3','Qwen3-1.7B v5'}
REN = {
 'amazon__nova-pro-v1':'Nova Pro','anthropic__claude-sonnet-4.5':'Claude Sonnet 4.5',
 'deepseek__deepseek-chat':'DeepSeek Chat','google__gemini-2.5-pro':'Gemini 2.5 Pro',
 'meta-llama__llama-3.3-70b-instruct':'Llama 3.3 70B','nvidia__nemotron-3-super-120b-a12b:free':'Nemotron 120B',
 'openai__gpt-4.1':'GPT-4.1','openai__gpt-4.1-mini':'GPT-4.1-mini','openai__gpt-4o-mini':'GPT-4o-mini',
 'openai__gpt-5.6-luna':'GPT-5.6 Luna','qwen__qwen-2.5-72b-instruct':'Qwen2.5 72B',
 'qwen__qwen3-235b-a22b-2507':'Qwen3 235B','qwen3-0.6b-masld':'Qwen3-0.6B v3',
 'qwen3-0.6b-masld-v5':'Qwen3-0.6B v5','qwen3-1.7b-masld':'Qwen3-1.7B v3',
 'qwen3-1.7b-masld-v5':'Qwen3-1.7B v5','inception__mercury-2.5':'Mercury-2.5'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'savefig.dpi':300,'savefig.bbox':'tight','savefig.pad_inches':0.04,'axes.spines.top':False,'axes.spines.right':False})
summary = list(csv.DictReader(open(AUD/'tissue_eligible_summary.tsv'), delimiter='\t'))
ranks = list(csv.DictReader(open(AUD/'tissue_eligible_ranks.tsv'), delimiter='\t'))
llm = json.loads((REV/'analysis/llm_binary_metrics.json').read_text())
reader = json.loads((REV/'analysis/reader_by_model.json').read_text())
gate = json.loads((REV/'analysis/gate_recompute.json').read_text())
tissue = json.loads((REV/'analysis/tissue_eligible.json').read_text())

# export machine-readable source tables
with open(TAB/'table2_tissue_coverage.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0].keys()));w.writeheader();w.writerows(summary)
with open(TAB/'figure2_eligible_ranks.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(ranks[0].keys()));w.writeheader();w.writerows(ranks)

# ---------- Figure 2: rank heatmaps ----------
cmap = LinearSegmentedColormap.from_list('r',['#12324f','#2a6f97','#8ecae6','#f4f1e8'])
fig, axes = plt.subplots(1,2,figsize=(7.4,6.4),gridspec_kw={'width_ratios':[1.35,1],'wspace':0.85})
tasks=['MB-2001','MB-2002','MB-2005','MB-2006','MB-2003']
labels=['Binary\n(n=163)','5-class\n(n=163)','Fibrosis MAE\n(n=162)','NAS MAE\n(n=163)','Pairwise\n(shared n=300)']
M=np.full((len(ranks),len(tasks)),np.nan)
for i,r in enumerate(ranks):
    for j,t in enumerate(tasks):
        M[i,j]=float(r[t]) if r[t] else np.nan
im=axes[0].imshow(M,cmap=cmap,aspect='auto',vmin=1,vmax=17)
axes[0].set_xticks(range(len(tasks)));axes[0].set_xticklabels(labels,fontsize=5.4)
axes[0].set_yticks(range(len(ranks)));axes[0].set_yticklabels([f"{r['model']} ({float(r['mean_rank_single4']):.1f})" for r in ranks],fontsize=5.4)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        axes[0].text(j,i,'—' if np.isnan(M[i,j]) else str(int(M[i,j])),ha='center',va='center',fontsize=5.4,color='white' if not np.isnan(M[i,j]) and M[i,j]<7 else '#1d3557')
axes[0].set_title('A  Eligible tissue ranks (mean over four single-sample tasks)',loc='left',fontsize=6.4,pad=7)
# plasma binary ranks, AMC values from reader_by_model
plasma_tasks=['MB-8901','MB-8911','MB-8921']
pmodels=sorted([m for m in llm if 'MB-8901' in llm[m] and 'MB-8911' in llm[m]], key=lambda m: llm[m]['MB-8901']['accuracy'])
acc={}
for m in pmodels:
    acc[(m,'MB-8901')]=llm[m]['MB-8901']['accuracy']
    acc[(m,'MB-8911')]=llm[m]['MB-8911']['accuracy']
    acc[(m,'MB-8921')]=reader['models'][m]['amc']['accuracy']
PM=np.zeros((len(pmodels),3))
for j,t in enumerate(plasma_tasks):
    ordered=sorted(pmodels,key=lambda m:-acc[(m,t)])
    prev=None;rank=1
    for i,m in enumerate(ordered):
        if prev is None or abs(acc[(m,t)]-prev)>1e-12: rank=i+1
        PM[pmodels.index(m),j]=rank;prev=acc[(m,t)]
axes[1].imshow(PM,cmap=cmap,aspect='auto',vmin=1,vmax=14)
axes[1].set_xticks(range(3));axes[1].set_xticklabels(['Reference','Second\ncohort','AMC reader'],fontsize=5.6)
axes[1].set_yticks(range(len(pmodels)));axes[1].set_yticklabels([REN.get(m,m) for m in pmodels],fontsize=5.2)
for i in range(PM.shape[0]):
    for j in range(3):
        axes[1].text(j,i,str(int(PM[i,j])),ha='center',va='center',fontsize=5.4,color='white' if PM[i,j]<7 else '#1d3557')
axes[1].set_title('B  Plasma binary ranks',loc='left',fontsize=6.4,pad=7)
fig.savefig(FIG/'Figure_2_ranks.png');plt.close(fig)

# ---------- Figure 3: eligible tissue + plasma reference cohort ----------
fig,axes=plt.subplots(1,2,figsize=(7.4,4.9),gridspec_kw={'wspace':0.62})
rows=[r for r in summary if r['roster']=='eligible' and r['task']=='MB-2001']
rows.sort(key=lambda r:float(r['accuracy']))
y=np.arange(len(rows))
for i,r in enumerate(rows):
    name=REN[r['model']];c=TEAL if name in COMPACT else NAVY
    axes[0].hlines(i,float(r['ci_lo']),float(r['ci_hi']),color=c,lw=.6,alpha=.5)
    axes[0].scatter(float(r['accuracy']),i,s=13,c=c,zorder=3)
axes[0].set_yticks(y);axes[0].set_yticklabels([REN[r['model']] for r in rows],fontsize=5.9)
axes[0].axvline(107/163,ls=(0,(2,2)),color=GREY,lw=.7)
axes[0].text(107/163,-.62,'majority 0.656',rotation=90,fontsize=5.3,color='#555555',va='bottom',ha='right')
axes[0].set_title('A  Tissue fibrosis, binary (eligible; n=163)',loc='left',pad=7,fontsize=7)
axes[0].set_xlabel('Accuracy');axes[0].set_xlim(0,1.02);axes[0].set_ylim(-.8,len(rows)-.2)
rows_b=[]
for m,tasks_ in llm.items():
    v=tasks_.get('MB-8901')
    if not v:continue
    kind='fail' if v['operational_errors']==v['n'] else ('never_yes' if v['sensitivity']==0 else 'ok')
    rows_b.append((v['accuracy'],REN.get(m,m),v['accuracy_ci'][0],v['accuracy_ci'][1],kind,v['sensitivity']))
rows_b.sort()
y=np.arange(len(rows_b))
for i,(acc,name,lo,hi,kind,sens) in enumerate(rows_b):
    c=RED if kind=='fail' else (TEAL if name in COMPACT else NAVY)
    axes[1].hlines(i,lo,hi,color=c,lw=.6,alpha=.5)
    axes[1].scatter(acc,i,s=13,c=c,zorder=3,marker='x' if sens==0 else 'o')
axes[1].set_yticks(y);axes[1].set_yticklabels([r[1] for r in rows_b],fontsize=5.9)
axes[1].axvline(.7143,ls=(0,(2,2)),color=GREY,lw=.7);axes[1].axvline(.7232,ls='-',color=RED,lw=.8,alpha=.85)
axes[1].text(.7143,-.62,'majority 0.714',rotation=90,fontsize=5.3,color='#555555',va='bottom',ha='right')
axes[1].text(.7232,len(rows_b)-.4,'logreg 0.723',rotation=90,fontsize=5.3,color=RED,va='top',ha='left')
axes[1].set_title('B  Plasma cfRNA, binary (MB-8901)',loc='left',pad=7,fontsize=7)
axes[1].set_xlabel("Accuracy  (× = model never answered 'yes'; red = evaluation failed)")
axes[1].set_xlim(0,1.02);axes[1].set_ylim(-.8,len(rows_b)-.2)
fig.savefig(FIG/'Figure_3_binary_corrected.png');plt.close(fig)

# ---------- Figure 4: format rank trajectories ----------
fig,ax=plt.subplots(figsize=(6.5,5.0))
xlabels=['Binary\n(n=163)','5-class\n(n=163)','Pairwise\n(shared n=300)','Fibrosis MAE\n(n=162)','NAS MAE\n(n=163)']
for r in ranks:
    vals=[float(r[t]) if r[t] else np.nan for t in ['MB-2001','MB-2002','MB-2003','MB-2005','MB-2006']]
    name=r['model'];c=TEAL if name in COMPACT else NAVY
    ax.plot(range(5),vals,'-o',ms=2.6,lw=.7,color=c,alpha=.55)
    if name in ['Claude Sonnet 4.5','Qwen3-0.6B v3','GPT-5.6 Luna','Qwen3-1.7B v5']:
        # Avoid overlapping labels; model values are in Supplementary Table S2.
        ax.annotate(name, (4, vals[-1]), xytext=(4.05, vals[-1] + (-0.4 if name == 'Qwen3-0.6B v3' else 0.4 if name == 'Qwen3-1.7B v5' else 0)), fontsize=5.4, color=c, va='center', arrowprops=dict(arrowstyle='-', color=c, lw=.4))
ax.set_xticks(range(5));ax.set_xticklabels(xlabels,fontsize=5.5)
ax.set_ylim(17.5,.5);ax.set_ylabel('Rank (1 = best; missing = different pairwise manifest)')
ax.set_title('Eligible-model rank instability across answer formats',loc='left',fontsize=7,pad=7)
fig.savefig(FIG/'Figure_4_format.png');plt.close(fig)

# ---------- Figure 5: regression MAE vs rho ----------
fig,axes=plt.subplots(1,2,figsize=(7.2,3.7),gridspec_kw={'wspace':.3})
for ax,task,title in zip(axes,['MB-2005','MB-2006'],['A  Fibrosis stage (n=162)','B  NAS (n=163)']):
    rr=[r for r in summary if r['roster']=='eligible' and r['task']==task and r['mae'] and r['spearman'] and r['spearman']!='nan']
    for r in rr:
        name=REN[r['model']];c=TEAL if name in COMPACT else NAVY
        ax.scatter(float(r['mae']),float(r['spearman']),s=18,c=c,alpha=.8)
        if False:  # Avoid overlapping labels; model values are in Supplementary Table S2.
            ax.annotate(name,(float(r['mae']),float(r['spearman'])),fontsize=5.0,xytext=(3,3),textcoords='offset points')
    ax.set_xscale('log');ax.set_xlabel('Conditional MAE (log scale)');ax.set_ylabel('Spearman ρ')
    ax.axhline(0,color=GREY,lw=.5);ax.set_title(title,loc='left',fontsize=6.8,pad=7)
fig.savefig(FIG/'Figure_5_regression.png');plt.close(fig)

# ---------- Figure S1: best model per developer, eligible only ----------
devs={'OpenAI':['GPT-4.1','GPT-4.1-mini','GPT-4o-mini','GPT-5.6 Luna'],'Anthropic':['Claude Sonnet 4.5'],'Google':['Gemini 2.5 Pro'],'Meta':['Llama 3.3 70B'],'Amazon':['Nova Pro'],'NVIDIA':['Nemotron 120B'],'DeepSeek':['DeepSeek Chat'],'Alibaba':['Qwen2.5 72B','Qwen3 235B'],'Compact v3/v5':sorted(COMPACT)}
dev_models={v:k for k,ms in devs.items() for v in ms}
fig,axes=plt.subplots(1,4,figsize=(8.0,3.4),gridspec_kw={'wspace':.35})
for ax,task in zip(axes,['MB-2001','MB-2002','MB-2005','MB-2006']):
    rr=[r for r in summary if r['task']==task and (r['roster']=='eligible' or r['roster'].startswith('pairwise_manifest'))]
    bydev={d:[] for d in devs}
    for r in rr:
        name=REN[r['model']]
        if name not in dev_models:continue
        val=float(r['accuracy']) if task in ['MB-2001','MB-2002','MB-2003'] else (float(r['mae']) if r['mae'] else np.nan)
        bydev[dev_models[name]].append((val,name))
    ds=list(devs);vals=[]
    for d in ds:
        candidates=bydev[d]
        if not candidates:vals.append((np.nan,'—'));continue
        val,name=(max(candidates) if task in ['MB-2001','MB-2002','MB-2003'] else min(candidates))
        vals.append((val,name))
    finite=[v for v,n in vals if np.isfinite(v)]
    norm=plt.Normalize(min(finite),max(finite)) if finite and min(finite)!=max(finite) else None
    for i,(v,name) in enumerate(vals):
        c='#2a6f97' if np.isfinite(v) and norm and norm(v)>.5 else '#dce6ec'
        ax.barh(i,1,color=c)
        txt='—' if not np.isfinite(v) else (f'{v:.3f}\n{name}' if v<100 else f'{v:.1e}\n{name}')
        ax.text(.5,i,txt,ha='center',va='center',fontsize=4.8)
    ax.set_yticks(range(len(ds)));ax.set_yticklabels(ds,fontsize=5.2);ax.set_xticks([])
    ax.set_title(task,fontsize=6.2)
fig.savefig(SUP/'Figure_S1.png');plt.close(fig)

# ---------- Figure S2: eligible tissue only; historical blood/cfRNA panels excluded ----------
fig,ax=plt.subplots(figsize=(6.8,5.8))
rr=[(REN[r['model']],float(r['accuracy']),float(r['ci_lo']),float(r['ci_hi'])) for r in summary if r['roster']=='eligible' and r['task']=='MB-2002']
rr.sort(key=lambda x:x[1])
for i,(name,v,lo,hi) in enumerate(rr):
    c=TEAL if name in COMPACT else NAVY
    ax.hlines(i,lo,hi,color=c,lw=.9);ax.scatter(v,i,color=c,s=18)
ax.set_yticks(range(len(rr)));ax.set_yticklabels([x[0] for x in rr],fontsize=8)
ax.axvline(43/163,color=GREY,lw=1,label='Observed majority 43/163 = 0.264')
ax.axvline(.2,color=GREY,ls='--',lw=1,label='Uniform-choice chance 0.200')
ax.set_xlim(0,.45);ax.set_xlabel('Five-class accuracy');ax.set_title('Eligible tissue models on 163 aligned items',loc='left')
ax.legend(frameon=False,fontsize=7,loc='lower right')
fig.savefig(SUP/'Figure_S2.png');plt.close(fig)

# ---------- Figure S3: AMC from fixed-prediction reader rescore ----------
def boot_acc(correct,n,seed=20260929):
    rng=np.random.default_rng(seed)
    vals=np.r_[np.ones(correct),np.zeros(n-correct)]
    idx=rng.integers(0,n,size=(2000,n))
    means=vals[idx].mean(axis=1)
    return float(np.percentile(means,2.5)),float(np.percentile(means,97.5))
fig,axes=plt.subplots(1,3,figsize=(10.6,5.6),gridspec_kw={'wspace':.45})
for ax,task,title,maj,gkey in [
    (axes[0],'MB-8901','A  Plasma binary, reference cohort',.7143,'MB-8901_logreg'),
    (axes[1],'MB-8911','B  Plasma binary, second cohort',.5307,'MB-8911_logreg'),
    (axes[2],'MB-8921','C  Plasma binary, AMC gold (fixed predictions)',.6759,'MB-8921_logreg')]:
    rr=[]
    if task!='MB-8921':
        for m,tasks_ in llm.items():
            v=tasks_.get(task)
            if not v:continue
            kind='fail' if v['operational_errors']==v['n'] else ('never_yes' if v['sensitivity']==0 else 'ok')
            rr.append((v['accuracy'],REN.get(m,m),v['accuracy_ci'][0],v['accuracy_ci'][1],kind,v['sensitivity']))
    else:
        for m,v in reader['models'].items():
            a=v['amc'];lo,hi=boot_acc(a['tp']+a['tn'],a['n'])
            rr.append((a['accuracy'],REN.get(m,m),lo,hi,'never_yes' if a['tp']==0 else 'ok',a['sensitivity']))
    rr.sort();y=np.arange(len(rr))
    for i,(acc,name,lo,hi,kind,sens) in enumerate(rr):
        c=RED if kind=='fail' else (TEAL if name in COMPACT else NAVY)
        ax.hlines(i,lo,hi,color=c,lw=.6,alpha=.5);ax.scatter(acc,i,s=13,c=c,marker='x' if sens==0 else 'o')
    ax.set_yticks(y);ax.set_yticklabels([r[1] for r in rr],fontsize=5.6)
    ax.axvline(maj,ls=(0,(2,2)),color=GREY,lw=.7)
    ax.text(maj,-.62,f'majority {maj:.3f}',rotation=90,fontsize=5.3,color='#555555',va='bottom',ha='right')
    g=gate.get(gkey,{})
    if g:
        ax.axvline(g['accuracy'],ls='-',color=RED,lw=.8,alpha=.85)
        ax.text(g['accuracy'],len(rr)-.4,f"logreg {g['accuracy']:.3f}",rotation=90,fontsize=5.3,color=RED,va='top',ha='left')
    ax.set_title(title,loc='left',pad=7,fontsize=6.4);ax.set_xlabel("Accuracy  (× = never answered 'yes'; red = evaluation failed)")
    ax.set_xlim(0,1.02);ax.set_ylim(-.8,len(rr)-.2)
fig.savefig(SUP/'Figure_S3.png');plt.close(fig)
# ---------- Figure S5: per-model rank-range diagnostic ----------
fig, ax = plt.subplots(figsize=(6.5, 4.0))
rr = []
for r in ranks:
    vals = [float(r[t]) for t in ['MB-2001', 'MB-2002', 'MB-2005', 'MB-2006']]
    rr.append((r['model'], max(vals) - min(vals), vals))
rr.sort(key=lambda x: x[1])
names = [x[0] for x in rr]
colors = [TEAL if n in COMPACT else NAVY for n in names]
ax.barh(range(len(rr)), [x[1] for x in rr], color=colors)
ax.set_yticks(range(len(rr)))
ax.set_yticklabels(names, fontsize=5.5)
ax.set_xlabel('Rank range across the four aligned single-sample tasks')
ax.set_title('Eligible-model format sensitivity (larger = less stable)', loc='left', fontsize=7, pad=7)
fig.savefig(SUP/'Figure_S5.png')
plt.close(fig)

# ---------- Figure S6: prediction-distribution compression ----------
per_item_path = Path(os.environ.get('MASLD_PER_ITEM_DIR', '')) / 'tissue_eligible_per_item.csv'
if not per_item_path.exists():
    print('skipping S6: MASLD_PER_ITEM_DIR not set (subject-level data not exported)')
else:
    per_item = list(csv.DictReader(open(per_item_path)))
    selected = [('Qwen3-1.7B v5', 'qwen3-1.7b-masld-v5'),
                ('Qwen3-1.7B v3', 'qwen3-1.7b-masld'),
                ('Llama 3.3 70B', 'meta-llama__llama-3.3-70b-instruct')]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.7), gridspec_kw={'wspace': .28})
    for ax, task, title in zip(axes, ['MB-2005', 'MB-2006'], ['A  Fibrosis stage', 'B  NAS']):
        gold = [float(r['gold']) for r in per_item
                if r['roster'] == 'eligible' and r['model'] == 'qwen3-1.7b-masld-v5' and r['task'] == task]
        data = [gold]
        labels = ['Gold']
        for name, model in selected:
            vals = [float(r['parsed']) for r in per_item
                    if r['roster'] == 'eligible' and r['model'] == model and r['task'] == task and r['valid'] == '1'
                    and ((task == 'MB-2005' and 0 <= float(r['parsed']) <= 4) or
                         (task == 'MB-2006' and 0 <= float(r['parsed']) <= 8))]
            data.append(vals)
            labels.append(name)
        ax.boxplot(data, tick_labels=labels, showfliers=False, widths=.55)
        ax.set_ylabel('Declared-domain value')
        ax.set_title(title, loc='left', fontsize=6.8, pad=7)
        ax.tick_params(axis='x', labelsize=5.2)
    fig.savefig(SUP/'Figure_S6.png')
    plt.close(fig)

# ---------- Figure S7: eligible-model valid-answer coverage ----------
tasks7 = ['MB-2001', 'MB-2002', 'MB-2003', 'MB-2005', 'MB-2006']
models7 = [r['model'] for r in ranks]
M = np.full((len(models7), len(tasks7)), np.nan)
for i, disp in enumerate(models7):
    model = next(m for m, n in REN.items() if n == disp)
    for j, task in enumerate(tasks7):
        candidates = [r for r in summary if r['model'] == model and r['task'] == task
                      and (r['roster'] == 'eligible' or r['roster'].startswith('pairwise_manifest'))]
        if candidates:
            r = candidates[0]
            M[i, j] = int(r['valid']) / int(r['n'])
fig, ax = plt.subplots(figsize=(5.4, 5.2))
im = ax.imshow(M, cmap='Blues', aspect='auto', vmin=0, vmax=1)
ax.set_xticks(range(len(tasks7)))
ax.set_xticklabels(tasks7, fontsize=5.4, rotation=30, ha='right')
ax.set_yticks(range(len(models7)))
ax.set_yticklabels(models7, fontsize=5.4)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if np.isfinite(M[i, j]):
            ax.text(j, i, f'{M[i,j]:.2f}', ha='center', va='center', fontsize=4.8,
                    color='white' if M[i,j] > .6 else '#1d3557')
fig.colorbar(im, ax=ax, label='valid / archived items', fraction=.035, pad=.03)
ax.set_title('Eligible-model valid-answer coverage', loc='left', fontsize=7, pad=7)
fig.savefig(SUP/'Figure_S7.png')
plt.close(fig)

print('regenerated Figures 2,3,4,5 and S1,S2,S3,S5,S7 (S6 requires MASLD_PER_ITEM_DIR)')
