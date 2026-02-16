import geopandas as gpd

print("Loading dataset...")
gdf = gpd.read_file("./data/geojsons/gcdf_light.geojson")  # or original file

print("Converting CRS...")
gdf = gdf.to_crs(4326)

print("Reducing to needed columns...")

keep_cols = [
    "Title",
    "Sector.Name",
    "Amount.(Constant.USD.2021)",
    "Commitment.Date.(MM/DD/YYYY)",
    "Actual.Implementation.Start.Date.(MM/DD/YYYY)",
    "Actual.Completion.Date.(MM/DD/YYYY)",
    "Status",
    "geometry"
]

# Keep only existing columns
gdf = gdf[[c for c in keep_cols if c in gdf.columns]]

print("Converting dates to string...")
for col in gdf.columns:
    if "Date" in col:
        gdf[col] = gdf[col].astype(str)

print("Converting to representative points...")
gdf["geometry"] = gdf.geometry.representative_point()

print("Saving optimized file...")
gdf.to_file("gcdf_minimal.geojson", driver="GeoJSON")

print("Done.")
