import sys, pathlib
sys.path.insert(0, 'src')
from src.data_acquisition.power import download_power_data
# download for Nairobi (1.3 S, 36.8 E) 2020-2024
df = download_power_data(latitude=-1.3, longitude=36.8, start_year=2020, end_year=2024)
print('Days:', len(df))
print(df.head())
# save
df.to_csv('data/processed/power_nairobi_2020_2024.csv', index=False)
print('Saved CSV.')