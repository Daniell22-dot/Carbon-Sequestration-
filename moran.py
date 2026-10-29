import math, numpy as np, pandas as pd

# project coordinates from cdr_projects.csv
proj = pd.read_csv('data/processed/cdr_projects.csv')
lat = proj['latitude'].values.astype(float)
lon = proj['longitude'].values.astype(float)
cost = proj['cost_per_ton'].values.astype(float)

# haversine distance matrix (km)
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c  # km

dist_matrix = np.zeros((3,3))
for i in range(3):
    for j in range(3):
        dist_matrix[i,j] = haversine(lon[i], lat[i], lon[j], lat[j])

# weights = inverse distance, zero on diagonal
w = np.zeros((3,3))
for i in range(3):
    for j in range(3):
        if i != j:
            w[i,j] = 1.0 / dist_matrix[i,j]

# row-standardize
row_sums = w.sum(axis=1)
w = w / row_sums[:, None]

# Moran's I
n = 3
x = cost
x_bar = np.mean(x)
S0 = w.sum()
numerator = np.sum(w * (x - x_bar).reshape(-1,1) * (x - x_bar).reshape(1,-1))
denominator = np.sum((x - x_bar)**2)
I = (n / S0) * numerator / denominator

print('Distance matrix (km):')
print(dist_matrix)
print('Row-standardized weights:')
print(w)
print(f"Moran's I = {I:.3f}")
print(f"Mean cost = {x_bar:.2f}")
print(f"Cost values: {cost}")