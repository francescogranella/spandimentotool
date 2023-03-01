# %% imports
import argparse
import pathlib
import os, sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
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
            print(os.getcwd())
            input_path = context.projectpath() / "data/example.parquet"
        elif example_answer == 'n':
            print('Bye!')
            sys.exit()
else:
    input_path = vars(args)['input']

print('Input:', input_path)
print('Output:', output_path)
print('Code comune', code)
print(context.projectpath())
print('\n')
# %% Process weather input
processed_weather_forecasts = preprocess_weather(input_path, nlags=3, drop_spandimento=False)
# Add population
popgrid = get_popgrid()
processed_weather_forecasts = pd.merge(popgrid.drop(columns='pop'), processed_weather_forecasts.reset_index(),
                                       on=['lon', 'lat'], how='inner')

if code:
    codcom = code
    mod = load_model(context.projectpath() / f'models/model_{codcom}')
    load_config(context.projectpath() / f'models/config_{codcom}')
    w = processed_weather_forecasts.copy()
    g = w[(w.codcom == codcom) & (w.date.isin(w.date.drop_duplicates().nlargest(10)))]
    g = g.sort_values(by='date')
    g['pred'] =  predict_model(mod, g.drop(columns='date')).rename(columns={'Label': 'pred'})[['pred']]
    g = pd.merge(g, popgrid, on=['lon', 'lat', 'codcom'], how='inner')
    prec = g.groupby('date').tp_l0.sum().reset_index()
    g = g.groupby(['date']).apply(lambda x: (x['pred'] * x['pop'] / x['pop'].sum()).sum()).reset_index().rename(
        columns={0: 'pred'})
    g = pd.merge(g, prec)

    from tabulate import tabulate
    res = g.rename(columns={'pred':'predicted PM2.5', 'tp_l0': 'total precipitation'}).round(2)
    res.to_csv(output_path, index=False)
    print(res)

    fig, (ax1, ax2) = plt.subplots(nrows=2, figsize=(12, 8), constrained_layout=False, dpi=80)
    ax1.plot(g.date, g.pred, zorder=1, color='black')
    ax1.axhline(20, color='red', zorder=0)
    ax1.axhline(15, color='salmon', zorder=0)
    ax1.set_ylim(0, ax1.get_ylim()[1])
    ax1.set_xticklabels(())
    ax1.spines[['top', 'right']].set_visible(False)
    ax1.grid(False)
    ax1.set_ylabel('PM$_{2.5}$, $\mu g/m^3$', fontsize=9)
    ax2.bar(g.date, g.tp_l0, color='deepskyblue', zorder=0)
    ax2.set_ylabel('Precipitation, mm', color='deepskyblue', fontsize=9)
    ax2.spines[['top', 'right']].set_visible(False)
    ax2.grid(False)
    ax2.set_xticklabels(g.date, rotation=45, ha='right')
    myFmt = mdates.DateFormatter('%b%d')
    ax2.xaxis.set_major_formatter(myFmt)
    oos = predict_model(mod)
    title = get_name_comune(codcom) + '\nRank-correlation: ' + str(np.round(spearmanr(oos.y, oos.Label)[0], 2))
    plt.suptitle(title)
    plt.show()

else:

    # %%
    from tqdm import tqdm

    l = []
    for codcom, g in tqdm(processed_weather_forecasts.groupby('codcom')):
        try:
            mod = load_model(context.projectpath() / f'models/model_{codcom}')
            load_config(context.projectpath() / f'models/config_{codcom}')
        except:
            continue
        g = g.sort_values(by='date')
        _g = g.iloc[-10:]
        predictions = predict_model(mod, _g.drop(columns='date')).rename(columns={'Label': 'pred'})[['pred']]
        predictions['codcom'] = codcom
        predictions['date'] = _g.date
        l.append(predictions)

    df = pd.concat(l)

    borders_comuni = get_borders_comuni()
    gdf = borders_comuni.merge(df, on=['codcom'], how='right')
    lomb = borders_comuni.dissolve()

    nrows = int(np.ceil(gdf.date.nunique() ** .5))
    ncols = int(np.floor(gdf.date.nunique() ** .5))

    fig, axs = plt.subplots(nrows, ncols, figsize=(15, 15), sharex=True, sharey=True)
    for i, (date, g) in enumerate(gdf.groupby('date')):
        ax = axs.flatten()[i]
        ax.spines[['top', 'bottom', 'left', 'right']].set_visible(False)
        lomb.boundary.plot(ax=ax)
        g.plot(column='pred', ax=ax, legend=True)
        ax.set_title(date)
    for ax in axs.flatten()[nrows * ncols - (nrows * ncols - gdf.date.nunique()):]:
        ax.set_visible(False)
    plt.tight_layout()
    plt.show()
