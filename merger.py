import geopandas as gpd
import pandas as pd
from pathlib import Path

folder = Path("data/geojsons")

gdfs = []

for file in folder.glob("*.geojson"):
    print(f"Reading {file.name}")
    gdf = gpd.read_file(file)
    gdfs.append(gdf)

print("Merging...")
merged = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

merged = merged.to_crs(4326)

print("Simplifying geometries...")
merged["geometry"] = merged.geometry.simplify(
    0.01,
    preserve_topology=True
)

print("Saving lightweight file...")
merged.to_file("data/gcdf_light.geojson", driver="GeoJSON")

print("Done.")
