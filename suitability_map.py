import sys, pathlib
sys.path.insert(0, 'src')
from src.visualization.maps import stations_geodataframe, projects_geodataframe, save_folium_map
import pandas as pd, folium

# projects data
proj_df = pd.read_csv('data/processed/cdr_projects.csv')
gdf_projects = projects_geodataframe(proj_df)

# assumed climate means (Nairobi region)
# TMAX ~30°C, TMIN ~18°C, annual precipitation ~700 mm
mean_TMAX = 30.0
mean_TMIN = 18.0
annual_PRECTOT = 700.0

# suitability: precipitation > 600 AND TMAX < 32
proj_df['suitable'] = (annual_PRECTOT > 600) & (mean_TMAX < 32)

# center map
gdf = projects_geodataframe(proj_df)
center = [gdf.geometry.y.mean(), gdf.geometry.x.mean()]
m = folium.Map(location=center, zoom_start=5)

for _, row in gdf.iterrows():
    color = 'green' if row['suitable'] else 'red'
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        popup=f"{row['project_name']}\nSuitable={row['suitable']}\nPrecip={annual_PRECTOT:.0f}mm\nTMAX={mean_TMAX:.1f}°C",
    ).add_to(m)

save_folium_map(m, 'output/figures/suitability_map.html')
print('Suitability map saved.')