import glob
import itertools
import os

import geopandas as gpd
import numpy as np
import pandas as pd
from tqdm import tqdm

from spandimentotool import context


def get_bounds():
    """:return minx maxx miny maxy"""
    miny = 44.6
    maxy = 46.7
    minx = 8.4
    maxx = 11.5
    return minx, maxx, miny, maxy


def down_unzip(url, path):
    import requests, zipfile, io
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(path)


def get_borders_comuni():
    borders_comuni_folder = context.projectpath() / 'data/borders'
    borders_comuni_path = context.projectpath() / 'data/borders/Limiti01012022_g/Com01012022_g/Com01012022_g_WGS84.shp'
    if not os.path.isfile(borders_comuni_path):
        down_unzip('https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/Limiti01012022_g.zip',
                   borders_comuni_folder)
    else:
        pass
    comuni = gpd.read_file(borders_comuni_path)
    aree = get_aree_spandimento()
    comuni = pd.merge(comuni[['PRO_COM', 'geometry']].rename(columns={'PRO_COM': 'codcom'}), aree, on=['codcom'],
                      how='inner')
    return comuni.to_crs('EPSG:4326')


def get_name_comune(codcom):
    borders_comuni_folder = context.projectpath() / 'data/borders'
    borders_comuni_path = context.projectpath() / 'data/borders/Limiti01012022_g/Com01012022_g/Com01012022_g_WGS84.shp'
    if not os.path.isfile(borders_comuni_path):
        down_unzip('https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/Limiti01012022_g.zip',
                   borders_comuni_folder)
    else:
        pass
    comuni = gpd.read_file(borders_comuni_path)
    return comuni.loc[comuni['PRO_COM_T'].astype(int)==codcom, 'COMUNE'].values[0]


def get_popgrid_ita():
    grid_ita_path = context.projectpath() / 'data/grid_ita.parquet'
    grid_ita = gpd.read_parquet(grid_ita_path)
    return grid_ita


def get_aree_spandimento():
    aree_path = context.projectpath() / 'data/aree_spandimento.csv'
    aree = pd.read_csv(aree_path)
    aree = aree[['Codice ISTAT', 'N. Zona Pedoclimatica']].rename(
        columns={'Codice ISTAT': 'codcom', 'N. Zona Pedoclimatica': 'narea'})
    return aree


def get_name_aree_spandimento():
    aree_path = context.projectpath() / 'data/aree_spandimento.csv'
    aree = pd.read_csv(aree_path)
    return aree[['Zona Pedoclimatica', 'N. Zona Pedoclimatica']].rename(
        columns={'Zona Pedoclimatica': 'name', 'N. Zona Pedoclimatica': 'narea'}).drop_duplicates().set_index(
        'narea').to_dict()['name']


def get_popgrid():
    grid_path = context.projectpath() / 'data/popgrid.parquet'
    if not os.path.isfile(grid_path):
        grid_ita = get_popgrid_ita()
        minx, maxx, miny, maxy = get_bounds()
        grid_lomb = grid_ita.cx[minx:maxx, miny:maxy]
        # Add codcom
        borders_aree = get_borders_comuni()
        grid_lomb = gpd.sjoin(grid_lomb.rename(columns={'Pop': 'pop'}), borders_aree, how='inner', op='intersects')  #[['pop', 'codcom', 'geometry']]
        lon = np.round(grid_lomb.centroid.x * 10) / 10  # round to nearest nth
        lat = np.round(grid_lomb.centroid.y * 10) / 10
        grid_lomb['lon'] = lon
        grid_lomb['lat'] = lat
        grid = grid_lomb.groupby(['lon', 'lat', 'codcom'])['pop'].sum().reset_index()
        grid['codcom'] = grid['codcom'].astype(int)
        grid.to_parquet(grid_path)
    else:
        grid = pd.read_parquet(grid_path)
    return grid


def get_grid_areas():
    # dummy_data_path = context.projectpath() / "/data/out/wp3/ecmwf.parquet"
    # df = pd.read_parquet(dummy_data_path)
    # df.sort_index(inplace=True)
    # df = df[df.time == df.time.min()]
    # df = df[['lon', 'lat']].drop_duplicates()
    # gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs='EPSG:4326')
    # borders_aree = get_borders_comuni().dissolve(by='narea').reset_index()
    # gdf = gpd.sjoin(gdf, borders_aree, op='within')[['lon', 'lat', 'narea']]
    # return pd.merge(df, gdf, on=['lon', 'lat'], how='inner').drop(columns='geometry')
    return pd.read_parquet(context.projectpath() / 'data/grid_areas.parquet')


# def make_pollution_data(overwrite=False):
#     file_path = context.projectpath() / '/data/out/wp3/pollution.parq'
#     if not os.path.isfile(file_path) or overwrite:
#
#         files = glob.glob(context.projectpath() / '/data/out/pollution/*.parq')
#         l = []
#         for file in tqdm(files):
#             print(file)
#             _df = pd.read_parquet(file)
#             _df = _df[_df.valid == 1]
#             _df['date'] = _df.data.dt.date
#             _df = _df.groupby(['idsensore', 'date'])['valore'].mean().reset_index()
#             l.append(_df)
#         df = pd.concat(l)
#
#         meta = pd.read_parquet(context.projectpath() / '/data/out/PollutionStations.parq')
#         meta = meta[pd.isna(meta['datastop']) == True]
#         meta = meta[meta.pollutantshort == 'PM2.5']
#
#         df = pd.merge(df, meta[['idsensore', 'idstazione', 'lat', 'lng']], how='inner', on='idsensore', validate='m:1')
#         df['date'] = pd.to_datetime(df['date'])
#         # Drop eventual duplicates
#         df.drop_duplicates(keep='first', inplace=True)
#         # df = df.groupby('date')['valore'].mean()
#         df.to_parquet(file_path)
#     else:
#         df = pd.read_parquet(file_path)
#     return df


def preprocess_weather(path, nlags=0, drop_spandimento=True):
    # Weather: open, create wind dir+speed, subset
    weather = pd.read_parquet(path)
    weather = weather[weather.lsm > 0.75]
    minx, maxx, miny, maxy = get_bounds()
    weather = weather[(weather.lon.between(minx, maxx)) & (weather.lat.between(miny, maxy))]
    # used_cols = ['T2M', 'precip', 'U10M', 'V10M']
    # assert set(used_cols).issubset(weather.columns)
    weather = weather[['time', 'lat', 'lon', '10u', '10v', '2t', 'tp', ]]

    # Wind speed and direction
    weather['wspeed'] = (weather['10u'] ** 2 + weather['10v'] ** 2) ** 0.5  # assume is in radians
    weather['wdir'] = (270 - np.rad2deg(np.arctan2(weather['10v'], weather['10u']))) % 360
    for i in range(4):
        mindeg = i * 90
        maxdeg = mindeg + 90
        weather[f'wspeed_{mindeg}_{maxdeg}'] = np.where(weather.wdir.between(mindeg, maxdeg), weather.wspeed, 0)
    # keep_cols = ['time', 'lat', 'lon', 'T2M', 'precip'] + list \
    #     (weather.filter(like='wspeed_').columns)
    # weather = weather[keep_cols]
    weather.drop(columns=['10u', '10v', 'wspeed', 'wdir'], inplace=True)
    for col in weather.columns:
        if col not in ['time', 'lat', 'lon']:
            weather[col] = weather[col].round(2)

    # weather = weather.pivot(index=['time'], columns=['lat', 'lon'])
    # weather.columns = ['_'.join([str(c) for c in x]) for x in weather   .columns]

    # Weather: aggregate on time
    weather['date'] = weather.time.dt.date
    agg_dict = dict(
        zip([x for x in weather.columns if x not in ['time', 'date', 'tp', 'lon', 'lat']], itertools.repeat('mean')))
    agg_dict['tp'] = 'sum'
    weather = weather.groupby(['date', 'lon', 'lat']).agg(agg_dict).reset_index()

    # Weather:interpolate
    popgrid = get_popgrid()
    popds = popgrid.set_index(['lat', 'lon', 'codcom']).to_xarray()
    ds = weather.set_index(['date', 'lat', 'lon']).to_xarray()
    dsi = ds.interp_like(popds, method='nearest')
    weather = dsi.to_dataframe().reset_index()

    # Weather :Aggregate on space
    # weather = weather.groupby(['date', 'codcom']).mean().reset_index().drop(columns=['lat', 'lon'])

    # Weather: lags
    if nlags>0:
        l = []
        for (lat, lon), g in weather.groupby(['lat', 'lon'], sort=False):
            pass
            l2 = []
            g = g.sort_values(by='date').set_index(['date', 'lat', 'lon'])
            for i in range(nlags):
                _g = g.shift(i)
                _g.columns = ['_'.join([x, f'l{i}']) for x in _g.columns]
                l2.append(_g)
            l.append(pd.concat(l2, axis=1))
        weather = pd.concat(l).reset_index()
    weather.set_index('date', inplace=True)

    # Time
    weather.index = pd.DatetimeIndex(weather.index)
    weather = weather[weather.index.month.isin([1, 2, 3, 4, 10, 11, 12])]
    weather = weather[(weather.index < '2020-02-21') | (weather.index > '2020-05-04')]
    weather['dow'] = weather.index.dayofweek
    weather['week'] = weather.index.week

    # Spandimento
    if drop_spandimento:
        spandimento_df = get_spandimento()
        _min, _max = spandimento_df.date.min(), spandimento_df.date.max()
        no_spandimento_dates = spandimento_df[spandimento_df.allowed==1].date
        weather = weather[(weather.index < _max) & (weather.index > _min)]
        weather = weather[weather.index.isin(no_spandimento_dates)]
    return weather


def get_spandimento():
    path = context.projectpath() / '/data/out/spandimento.parq'
    df = pd.read_parquet(path)
    df = df.replace({'Alpi': 1, 'Prealpi_occidentali':2, 'Prealpi_orientali':3, 'Pianura_occidentale':4, 'Pianura_centrale':5, 'Pianura_orientale':6}).rename(columns={'zone':'narea'})
    df = df.dropna()
    return df