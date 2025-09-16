import streamlit as st
import folium
import pandas as pd
import numpy as np
from folium import plugins
import requests
from io import BytesIO

url_excel = "https://www.dropbox.com/scl/fi/ga1h4qhl6b1dlodzyparj/Farmacias-Chile-15.01.2024.xlsx?dl=1"

# Descargar el archivo con requests
response = requests.get(url_excel)
response.raise_for_status()  # Lanza error si la descarga falla

# Leer como Excel desde memoria
df = pd.read_excel(BytesIO(response.content), engine="openpyxl")

df['Latitud'] = df['Latitud'].astype(float)
df['Longitud'] = df['Longitud'].astype(float)

def clean_coordinate(coord):
    if pd.isna(coord):
        return np.nan
    try:
        coord_str = str(coord).strip()
        coord_str = coord_str.replace(' ', '').replace(',', '.')
        return float(coord_str)
    except:
        return np.nan

df['Latitud'] = df['Latitud'].apply(clean_coordinate)
df['Longitud'] = df['Longitud'].apply(clean_coordinate)

# Indicamos valores lógicos de latitud y longitud
df.loc[df['Latitud'] > -17, 'Latitud'] = np.nan
df.loc[df['Latitud'] < -56, 'Latitud'] = np.nan
df.loc[df['Longitud'] > -66, 'Longitud'] = np.nan
df.loc[df['Longitud'] < -109, 'Longitud'] = np.nan

df['Latitud'] = df['Latitud'].round(6)
df['Longitud'] = df['Longitud'].round(6)

print("Valores nulos en Latitud:", df['Latitud'].isna().sum())
print("Valores nulos en Longitud:", df['Longitud'].isna().sum())

df = df[df["Región"].str.upper() == "METROPOLITANA"]

df = df.dropna(subset=['Latitud', 'Longitud'])

# Verificamos resultados
print(f"Filas originales: {len(df)}")
print(f"Filas después de limpieza: {len(df)}")
print(f"Filas eliminadas: {len(df) - len(df)}")

print("\nEjemplo de datos limpios:")
print(df[['Latitud', 'Longitud']].head())

df.loc[620, ['Latitud', 'Longitud']] = [-33.2157073, -70.6732031]
df.loc[1625, ['Latitud', 'Longitud']] = [-33.6122126, -70.6277303]
df.loc[3882, ['Latitud', 'Longitud']] = [-33.4097461, -70.6955015]
df.loc[3892, ['Latitud', 'Longitud']] = [-33.4503, -70.7057]
df.loc[2570, ['Latitud', 'Longitud']] = [-33.4566, -70.6166]

df = df.drop_duplicates(subset=['Latitud', 'Longitud'])
df

df.loc[971, ['Latitud', 'Longitud']] = [-33.4056251, -71.1387927]

df.columns = df.columns.str.strip().str.replace('\xa0', ' ')

df.reset_index(drop=True, inplace=True)
df

url_parquet = "https://www.dropbox.com/scl/fi/d0i1mweir1wqid17oqv1w/Microdatos_Manzana.parquet?dl=1"

response = requests.get(url_parquet)
response.raise_for_status()

dbf = pd.read_parquet(BytesIO(response.content), engine="pyarrow")

def fix_encoding(s):
    if isinstance(s, str):
        try:
            return s.encode("latin1").decode("utf-8")
        except:
            return s
    return s

dbf = dbf.applymap(fix_encoding)
dbf = dbf[dbf['REGION'] == 'REGIÓN METROPOLITANA DE SANTIAGO'].copy()
# ----------------------------
# Limpiar nombres de comunas
# ----------------------------
df['Comuna_clean'] = df['Comuna'].str.upper().str.strip()
dbf['COMUNA_clean'] = dbf['COMUNA'].str.upper().str.strip()

# ----------------------------
# Definir comunas rurales
# ----------------------------
rurales = [
    "ALHUE", "CURACAVI", "ISLA DE MAIPO", "LAMPA", "MARIA PINTO",
    "MELIPILLA", "PAINE", "PEÑAFLOR", "PIRQUE", "SAN JOSE DE MAIPO",
    "SAN PEDRO", "TALAGANTE", "TIL TIL", "BUIN", "CALERA DE TANGO",
    "EL MONTE", "PADRE HURTADO"
]

# ----------------------------
# Crear mapa base centrado
# ----------------------------
centro_lat = dbf["y_man"].mean()
centro_lon = dbf["x_man"].mean()
m = folium.Map(location=[centro_lat, centro_lon], zoom_start=10)

# ----------------------------
# Capa de farmacias (círculos rojos según zona)
# ----------------------------
for _, row in df.iterrows():
    comuna = row['Comuna_clean']
    radio = 2500 if comuna in rurales else 1000  # 2.5 km rural, 1 km urbana

    folium.Circle(
        location=[row["Latitud"], row["Longitud"]],
        radius=radio,
        color="red",
        fill=True,
        fill_color="red",
        fill_opacity=1  # rojo sólido
    ).add_to(m)
# ----------------------------
# Capa de población (círculos de colores por comuna)
# ----------------------------

# Obtener una lista de comunas únicas y asignar un color a cada una
unique_comunas = dbf['COMUNA_clean'].unique()
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
          '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5']
color_map = {comuna: colors[i % len(colors)] for i, comuna in enumerate(unique_comunas)}


for _, row in dbf.iterrows():
    comuna_color = color_map.get(row['COMUNA_clean'], '#000000') # Default to black if comuna not in map

    folium.CircleMarker(
        location=[row["y_man"], row["x_man"]],
        radius=0.5,
        color=comuna_color,
        fill=True,
        fill_color=comuna_color,
        fill_opacity=0.4,
        popup=row["COMUNA_clean"], # Add popup for comuna name
        tooltip=row["COMUNA_clean"] # Add tooltip for comuna name on hover
    ).add_to(m)




# ----------------------------
# Mostrar mapa
# ----------------------------
