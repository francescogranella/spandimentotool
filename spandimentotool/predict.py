# %% imports
import argparse
import pathlib
import os, sys

import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import pandas as pd
from pycaret.regression import *
from scipy.stats import spearmanr

from spandimentotool import context
from spandimentotool.utils import get_name_comune
from spandimentotool.utils import preprocess_weather, get_borders_comuni, get_popgrid

# %%
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", help="path to input file", default='', required=False)
parser.add_argument("-o", "--output", help="path to output file", default='output.csv', required=False)
parser.add_argument("-c", "--code", help="Code comune", required=False, default=15146)
args = parser.parse_args()
code = int(vars(args)['code'])
output_path = vars(args)['output']

if vars(args)['input'] == '':
    example_answer = None
    while example_answer not in ['y', 'n']:
        example_answer = input('No input file or example file selected. Do you want to run an example? y/n\n')
        if example_answer == 'y':
            import os
            input_path = context.projectpath() / "data/example.parquet"
        elif example_answer == 'n':
            print('Bye!')
            sys.exit()
else:
    input_path = vars(args)['input']

print('Input:', input_path)
print('Output:', output_path)
print('Code comune', code)
print('\n')
# %% Process weather input
processed_weather_forecasts = preprocess_weather(input_path, nlags=3, drop_spandimento=False)
# Add population
popgrid = get_popgrid()
processed_weather_forecasts = pd.merge(popgrid.drop(columns='pop'), processed_weather_forecasts.reset_index(),
                                       on=['lon', 'lat'], how='inner')

mod = load_model(context.projectpath() / f'models/model_{code}_nospand')
load_config(context.projectpath() / f'models/config_{code}_nospand')
w = processed_weather_forecasts.copy()
g = w[(w.codcom == code) & (w.date.isin(w.date.drop_duplicates().nlargest(10)))]
g = g.sort_values(by='date')
g['pred'] = predict_model(mod, g.drop(columns='date')).rename(columns={'Label': 'pred'})[['pred']]
g = pd.merge(g, popgrid, on=['lon', 'lat', 'codcom'], how='inner')
prec = g.groupby('date').tp_l0.sum().reset_index()
g = g.groupby(['date']).apply(lambda x: (x['pred'] * x['pop'] / x['pop'].sum()).sum()).reset_index().rename(
    columns={0: 'pred'})
g = pd.merge(g, prec)

res = g.rename(columns={'pred': 'predicted PM2.5', 'tp_l0': 'total precipitation'}).round(2)
res.to_csv(output_path, index=False)
print(res)

ranking = g.sort_values(by='date', ascending=False).rolling(2, on='date', min_periods=1, closed='right').mean().sort_values(by='date', ascending=True)
ranking['prec>0'] = (ranking.tp_l0 > 0).astype(int)
ranking = ranking.sort_values(by=['prec>0', 'pred'], ascending=[True, True]).reset_index(drop=True).reset_index()

ranking['index'] += 1
ranking['date'] = ranking.date.dt.strftime('%b %d')
# ranking['pred'] = ranking['pred'].astype(float).round(2).astype(str)
# ranking['tp_l0'] = ranking['tp_l0'].astype(float).round(2).astype(str)
ranking = ranking[['index', 'date']]

fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, figsize=(8, 8), constrained_layout=False, dpi=100)
ax1.plot(g.date, g.pred, zorder=1, color='black')
ax1.axhline(25, color='red', zorder=0)
ax1.axhline(15, color='salmon', zorder=0)
ax1.set_ylim(0, ax1.get_ylim()[1])
ax1.set_xticklabels(())
ax1.spines[['top', 'right']].set_visible(False)
ax1.grid(False)
ax1.set_ylabel('PM$_{2.5}$, $\mu g/m^3$', fontsize=12)
custom_lines = [Line2D([0], [0], color='red', lw=4, label='Proposed EU standards'), Line2D([0], [0], color='salmon', lw=4, label='WHO standards')]
ax1.legend(handles=custom_lines, frameon=False)
ax2.bar(g.date, g.tp_l0, color='deepskyblue', zorder=0)
ax2.set_ylabel('Precipitation, mm', color='deepskyblue', fontsize=12)
ax2.spines[['top', 'right']].set_visible(False)
ax2.grid(False)
ax2.set_xticklabels(g.date, rotation=45, ha='right')
ax3.table(cellText=ranking.values, colLabels=['Rank of best days for spreading', 'Date'], loc='center', cellLoc='center', edges='open')
ax3.axis('off')
ax3.axis('tight')
plt.subplots_adjust(hspace=0.35)
myFmt = mdates.DateFormatter('%b%d')
ax2.xaxis.set_major_formatter(myFmt)
oos = predict_model(mod)
title = get_name_comune(code) + '\nRank-correlation: ' + str(np.round(spearmanr(oos.y, oos.Label)[0], 2))
plt.suptitle(title)
plt.tight_layout()
plt.show()
