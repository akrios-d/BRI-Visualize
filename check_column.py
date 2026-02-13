import geopandas as gpd
g = gpd.read_file("data/OSM_Polygon.gpkg")
print(g.columns)