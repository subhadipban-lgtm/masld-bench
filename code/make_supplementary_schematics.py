#!/usr/bin/env python3
"""Draw the schematic supplementary figures (S4, S8) and the S9 reader matrix.

S4 and S8 are text schematics describing cohorts, preprocessing contracts and
evaluation quantities; cohort wording follows the manuscript ("reference
cohort", "second cfRNA cohort"). S9 replots the aggregate UZA/AMC reader
confusion matrix; it contains no patient-level identifiers. Outputs are
written as PNG and PDF beside the other supplementary figures.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.figure import Figure

REV = Path(__file__).resolve().parents[1]
SUP = REV / 'figures_supplementary'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'savefig.dpi': 300})

_savefig = Figure.savefig
def _dual_save(self, fname, *a, **kw):
    _savefig(self, fname, *a, **kw)
    p = Path(str(fname))
    if p.suffix == '.png':
        _savefig(self, p.with_suffix('.pdf'), bbox_inches='tight', pad_inches=.06)
Figure.savefig = _dual_save


def schematic(path, title, boxes, footer):
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.text(0, 1, title, fontsize=12, weight='bold', va='top')
    for i, (heading, text) in enumerate(boxes):
        x = .01 + (i % 2) * .51
        y = .83 - (i // 2) * .27
        ax.text(x, y, heading, fontsize=10, weight='bold', va='top', color='#1d3557')
        ax.text(x, y - .055, text, fontsize=9, va='top', linespacing=1.5)
    ax.text(.01, .025, footer, fontsize=8, va='bottom', color='#555555')
    fig.savefig(path, bbox_inches='tight'); plt.close(fig)


schematic(SUP / 'Figure_S4.png', 'Plasma cfRNA cohorts and preprocessing', [
    ('Reference cohort', '112 samples; biopsy-stage reference\nBinary majority 80/112 = 0.714\nFrozen top-200 expression panel'),
    ('Reader subset', '108 jointly staged reference-cohort samples\nExact agreement 56/108\nUnweighted kappa 0.400'),
    ('Second cfRNA cohort', '179 patients; clinical-consensus reference\n42-patient biopsy subpanel\nBinary majority 95/179 = 0.531'),
    ('Frozen representation', 'Gene-wise scaling across samples\nCorpus-wide panel and moments\nTransductive classical evaluation'),
    ('Training-only sensitivities', 'Panel selected within each training fold\nTraining-only gene-wise moments OR\nPer-sample standardisation'),
    ('External five-gene transfer', 'Align genes by Ensembl identifier\nFreeze reference-cohort-derived moments\nPaired comparison remains inconclusive')],
    'The AMC reader subset is not an independent external cohort.')

schematic(SUP / 'Figure_S8.png', 'Distinct evaluation quantities', [
    ('Resubstitution', 'Model evaluated on its training data\nReference-cohort five-gene accuracy 0.759'),
    ('Conditional classifier cross-validation', 'Panel and scaling held fixed\nReference-cohort five-gene accuracy 0.714'),
    ('Fully nested cross-validation', 'Panel, ranking and scaling re-derived\nTop-5 reference-cohort accuracy 0.723'),
    ('External transfer', 'Reference-cohort-fixed genes and transformation\nExternal accuracy 0.615'),
    ('Marginal-interval gate', 'Accuracy interval versus observed majority\nNot a paired superiority comparison'),
    ('Paired external comparison', '51 model wins; 36 baseline wins\nExact McNemar p = 0.133')],
    'These quantities answer different questions; point estimates alone do not establish an advantage.')

# Aggregate reader matrix on the 108 jointly staged samples (corrected reader
# agreement); reproduced from the corrected analysis, no identifiers included.
M = np.array([[11, 16, 4, 1, 0],
              [0, 14, 8, 0, 0],
              [1, 3, 12, 8, 0],
              [0, 0, 4, 6, 5],
              [0, 0, 0, 2, 13]])
assert M.sum() == 108 and np.trace(M) == 56
fig, ax = plt.subplots(figsize=(5, 5))
ax.imshow(M, cmap='Blues')
ax.set_xticks(range(5), [f'F{i}' for i in range(5)])
ax.set_yticks(range(5), [f'F{i}' for i in range(5)])
for (i, j), v in np.ndenumerate(M):
    ax.text(j, i, str(v), ha='center', va='center', color='white' if v >= 10 else '#1d3557')
ax.set_xlabel('AMC reader stage'); ax.set_ylabel('UZA reader stage')
ax.set_title('Reader agreement on 108 jointly staged samples\nExact 56/108; unweighted κ 0.400; quadratic κ 0.809', fontsize=10)
fig.savefig(SUP / 'Figure_S9.png', bbox_inches='tight'); plt.close(fig)

print('wrote Figures S4, S8 and S9 (PNG and PDF)')
