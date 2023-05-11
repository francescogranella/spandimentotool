# %% imports
import pathlib

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import streamlit as st
import xarray as xr
from matplotlib.lines import Line2D
from pycaret.regression import *
from scipy.stats import spearmanr

from spandimentotool import context
from spandimentotool.utils import get_name_comune, save_municipalities
from spandimentotool.utils import preprocess_weather, get_popgrid

st.set_page_config(layout="centered")

# %
if pathlib.Path('municipalities.csv'):
    municipalities = pd.read_csv('municipalities.csv')
else:
    save_municipalities()
    municipalities = pd.read_csv('municipalities.csv')
with st.sidebar:
    option = st.selectbox(
        'Selezionare il comune',
        municipalities.name.sort_values())

    code = municipalities.loc[municipalities.name == option, 'code'].iloc[0]

    uploaded_file = st.file_uploader("Caricare le previsioni di ECMWF in formato NetCDF", type=['.nc', 'csv'],
                                     accept_multiple_files=False)

if uploaded_file is not None:
    import io
    import matplotlib

    with st.sidebar:
        ds = xr.open_dataset(io.BytesIO(uploaded_file.getvalue())).load()
        st.write('Uploaded data:')
        st.dataframe(ds.to_dataframe())

    # %% Process weather input
    processed_weather_forecasts = preprocess_weather(io.BytesIO(uploaded_file.getvalue()), nlags=3,
                                                     drop_spandimento=False)
    matplotlib.rcParams.update(matplotlib.rcParamsDefault)

    # Add population
    popgrid = get_popgrid()
    processed_weather_forecasts = pd.merge(popgrid.drop(columns='pop'), processed_weather_forecasts.reset_index(),
                                           on=['lon', 'lat'], how='inner')

    st.write('Previsioni per comune')
    w = processed_weather_forecasts.copy()

    mod = load_model(context.projectpath() / f'models/model_{code}_nospand')
    load_config(context.projectpath() / f'models/config_{code}_nospand')
    g = w[(w.codcom == code) & (w.date.isin(w.date.drop_duplicates().nlargest(10)))]
    g = g.sort_values(by='date')
    g['pred'] = predict_model(mod, g.drop(columns='date')).rename(columns={'Label': 'pred'})[['pred']]
    g = pd.merge(g, popgrid, on=['lon', 'lat', 'codcom'], how='inner')
    prec = g.groupby('date').tp_l0.sum().reset_index()
    g = g.groupby(['date']).apply(lambda x: (x['pred'] * x['pop'] / x['pop'].sum()).sum()).reset_index().rename(
        columns={0: 'pred'})
    g = pd.merge(g, prec)

    res = g.rename(columns={'pred': 'predicted PM2.5', 'tp_l0': 'total precipitation'}).round(2)

    ranking = g.sort_values(by='date', ascending=False).rolling(2, on='date', min_periods=1,
                                                                closed='right').mean().sort_values(by='date',
                                                                                                   ascending=True)
    ranking['prec>0'] = (ranking.tp_l0 > 0).astype(int)
    ranking = ranking.sort_values(by=['prec>0', 'pred'], ascending=[True, True]).reset_index(drop=True).reset_index()

    ranking['index'] += 1
    ranking['date'] = ranking.date.dt.strftime('%b %d')
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
    custom_lines = [Line2D([0], [0], color='red', lw=4, label='Proposed EU standards'),
                    Line2D([0], [0], color='salmon', lw=4, label='WHO standards')]
    ax1.legend(handles=custom_lines, frameon=False)
    ax2.bar(g.date, g.tp_l0 * 1000, color='deepskyblue', zorder=0)
    ax2.set_ylabel('Precipitation, mm', color='deepskyblue', fontsize=12)
    ax2.spines[['top', 'right']].set_visible(False)
    ax2.grid(False)
    ax2.set_xticklabels(g.date, rotation=45, ha='right')
    ax3.table(cellText=ranking.values, colLabels=['Rank of best days for spreading', 'Date'], loc='center',
              cellLoc='center', edges='open')
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
    st.pyplot(fig)
