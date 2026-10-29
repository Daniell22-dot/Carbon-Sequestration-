import sys
sys.path.insert(0, 'src')
from src.visualization.maps import stations_geodataframe, projects_geodataframe, save_folium_map
import pandas as pd, folium

# stations
gdf_stations = stations_geodataframe()

# projects
proj_df = pd.read_csv('data/processed/cdr_projects.csv')
gdf_projects = projects_geodataframe(proj_df)

# center
center = [gdf_stations.geometry.y.mean(), gdf_stations.geometry.x.mean()]
m = folium.Map(location=center, zoom_start=5)

# add station markers (blue)
for _, row in gdf_stations.iterrows():
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        popup=f"Station {row['name']}",
        icon=folium.Icon(color='blue', icon='info-sign'),
    ).add_to(m)

# add project markers (orange)
for _, row in gdf_projects.iterrows():
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        popup=f"Project {row['project_name']} – {row['method']}",
        icon=folium.Icon(color='orange', icon='leaf'),
    ).add_to(m)

save_folium_map(m, 'output/figures/stations_and_projects.html')
print('Map saved.')