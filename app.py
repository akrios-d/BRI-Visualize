from pathlib import Path
import json
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, HeatMap

from utils import (
    read_geopackage,
    read_geojson_folder,
    to_wgs84,
    detect_columns,
    simplify_geometries,
)

# ---------------------------------------------------
# UI Setup
# ---------------------------------------------------

st.set_page_config(page_title="GCDF–BRI Local Map", layout="wide")
st.title("GCDF – BRI Local Map (Offline)")
st.caption("Load a GeoPackage (.gpkg) or a folder of project GeoJSONs to explore Chinese-financed projects and overlays locally.")

# ---------------------------------------------------
# SIDEBAR – Data Source
# ---------------------------------------------------

with st.sidebar:
    st.header("Data Source")

    src_type = st.radio(
        "Choose input type",
        ["GeoPackage (.gpkg)", "Folder of GeoJSONs"]
    )

    data_dir = Path("data")

    if src_type == "GeoPackage (.gpkg)":
        gpkg_files = sorted([p for p in data_dir.glob("*.gpkg")])

        if gpkg_files:
            gpkg = st.selectbox(
                "Select GeoPackage in ./data",
                gpkg_files,
                format_func=lambda p: p.name,
            )
        else:
            gpkg = None
            st.info("No .gpkg file found in ./data. Add one or switch to 'Folder of GeoJSONs'.")

    else:
        geojson_folder = st.text_input(
            "Path to GeoJSON folder (default: ./data/geojsons)",
            "data/geojsons"
        )
        geojson_folder = Path(geojson_folder)

    # ---------------------------------------------------
    # Map Settings
    # ---------------------------------------------------

    st.divider()
    st.header("Map Settings")

    simplify = st.checkbox("Simplify geometries (faster)", True)
    tolerance = st.slider(
        "Simplify tolerance (degrees)",
        0.0005,
        0.01,
        0.002,
        0.0005
    )
    show_heatmap = st.checkbox("Density Heatmap (points)", False)

    # ---------------------------------------------------
    # Overlays
    # ---------------------------------------------------

    st.divider()
    st.header("Overlays")

    overlay_files = list(Path("overlays").glob("*.geojson"))
    selected_overlays = st.multiselect(
        "Overlay GeoJSONs in ./overlays",
        overlay_files,
        format_func=lambda p: p.name,
    )

# ---------------------------------------------------
# Load data
# ---------------------------------------------------

@st.cache_data(show_spinner=False)
def load_data(src_type, gpkg, geojson_folder):
    if src_type == "GeoPackage (.gpkg)":
        gdf = read_geopackage(gpkg)
    else:
        gdf = read_geojson_folder(geojson_folder)

    return to_wgs84(gdf)


try:
    if src_type == "GeoPackage (.gpkg)":
        if gpkg is None:
            st.warning("No GeoPackage selected. Drop one into ./data or choose GeoJSON mode.")
            st.stop()

        gdf = load_data(src_type, gpkg, None)

    else:
        gdf = load_data(src_type, None, geojson_folder)

except Exception as e:
    st.error(f"Load a dataset to begin. Error: {e}")
    st.stop()

# ---------------------------------------------------
# Column detection
# ---------------------------------------------------

cols = detect_columns(gdf)

# ---------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------

with st.sidebar:
    st.header("Filters")

    # Country filter
    if cols["country"] and cols["country"] in gdf.columns:
        countries = sorted(gdf[cols["country"]].dropna().astype(str).unique())
        sel_countries = st.multiselect("Country", countries)
    else:
        sel_countries = []

    # Sector filter
    if cols["sector"] and cols["sector"] in gdf.columns:
        sectors = sorted(gdf[cols["sector"]].dropna().astype(str).unique())
        sel_sectors = st.multiselect("Sector", sectors)
    else:
        sel_sectors = []

    # Year filter
    if cols["year"] and cols["year"] in gdf.columns:
        yrs = pd.to_numeric(gdf[cols["year"]], errors="coerce").dropna()
        if not yrs.empty:
            yr_min, yr_max = int(yrs.min()), int(yrs.max())
            yr_range = st.slider("Year range", yr_min, yr_max, (yr_min, yr_max))
        else:
            yr_range = None
    else:
        yr_range = None

    # Precision filter
    if cols["precision"] and cols["precision"] in gdf.columns:
        prec_vals = sorted(gdf[cols["precision"]].dropna().astype(str).unique())
        sel_prec = st.multiselect("Geographic precision", prec_vals)
    else:
        sel_prec = []

    # Value bucket
    if cols["value"] and cols["value"] in gdf.columns:
        vs = pd.to_numeric(gdf[cols["value"]], errors="coerce")
        bucket_choice = st.multiselect("Financing bucket", ["Low", "Medium", "High"])
    else:
        bucket_choice = []

# ---------------------------------------------------
# Apply filters
# ---------------------------------------------------

filtered = gdf.copy()

if sel_countries:
    filtered = filtered[filtered[cols["country"]].astype(str).isin(sel_countries)]

if sel_sectors:
    filtered = filtered[filtered[cols["sector"]].astype(str).isin(sel_sectors)]

if yr_range and cols["year"]:
    yy = pd.to_numeric(filtered[cols["year"]], errors="coerce")
    filtered = filtered[(yy >= yr_range[0]) & (yy <= yr_range[1])]

if sel_prec and cols["precision"]:
    filtered = filtered[filtered[cols["precision"]].astype(str).isin(sel_prec)]

if bucket_choice and cols["value"]:
    vs = pd.to_numeric(filtered[cols["value"]], errors="coerce")
    q1, q2 = vs.quantile(0.33), vs.quantile(0.66)

    def bucket(v):
        if pd.isna(v): return None
        if v <= q1: return "Low"
        if v <= q2: return "Medium"
        return "High"

    b = vs.apply(bucket)
    filtered = filtered[b.isin(bucket_choice)]

if simplify:
    filtered = simplify_geometries(filtered, tolerance)

# ---------------------------------------------------
# JSON sanitization helper
# ---------------------------------------------------

def sanitize_for_json(gdf_in: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Ensure all attribute columns are JSON serializable:
    - Convert datetime-like columns to ISO strings.
    - Also convert individual pd.Timestamp values inside object columns.
    """
    gdf = gdf_in.copy()
    for col in gdf.columns:
        # Skip geometry; Folium handles via .to_json() geometry output
        if col == "geometry":
            continue

        # Convert pandas datetime dtypes to string
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
            continue

        # For object columns, convert individual pd.Timestamp safely
        if pd.api.types.is_object_dtype(gdf[col]):
            gdf[col] = gdf[col].apply(
                lambda x: x.isoformat() if isinstance(x, pd.Timestamp) else x
            )
    return gdf

# ---------------------------------------------------
# Map rendering
# ---------------------------------------------------

st.subheader("Map")

if not filtered.empty and filtered.geometry.notnull().any():
    rp = filtered.geometry.representative_point()
    center = [rp.y.mean(), rp.x.mean()]
else:
    center = [0, 0]

m = folium.Map(location=center, zoom_start=2, tiles="cartodbpositron")

pts = filtered[filtered.geometry.geom_type.isin(["Point", "MultiPoint"])]
lines = filtered[filtered.geometry.geom_type.isin(["LineString", "MultiLineString"])]
polys = filtered[filtered.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]

# Sanitize attributes for JSON serialization before passing to Folium
pts = sanitize_for_json(pts)
lines = sanitize_for_json(lines)
polys = sanitize_for_json(polys)

# Points layer
if len(pts):
    mc = MarkerCluster(name="Projects (points)", disableClusteringAtZoom=7)
    for _, r in pts.iterrows():
        try:
            if r.geometry is None:
                continue
            lat, lon = r.geometry.y, r.geometry.x
            popup_fields = {k: ("" if k == "geometry" else str(r[k])) for k in r.index}
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(f"<pre>{json.dumps(popup_fields, indent=2)}</pre>", max_width=400),
                icon=folium.Icon(color="red", icon="info-sign"),
            ).add_to(mc)
        except Exception:
            continue
    mc.add_to(m)

# Lines
if len(lines):
    folium.GeoJson(
        lines.to_json(),
        name="Projects (lines)",
        style_function=lambda x: {"color": "#1f78b4", "weight": 3, "opacity": 0.8},
    ).add_to(m)

# Polygons
if len(polys):
    folium.GeoJson(
        polys.to_json(),
        name="Projects (polygons)",
        style_function=lambda x: {
            "color": "#33a02c",
            "weight": 1.5,
            "fillColor": "#33a02c",
            "fillOpacity": 0.2,
        },
    ).add_to(m)

# Heatmap
if show_heatmap and len(pts):
    heat_data = [[g.geometry.y, g.geometry.x] for _, g in pts.iterrows() if g.geometry is not None]
    if heat_data:
        HeatMap(heat_data, name="Density heatmap", radius=12, blur=15).add_to(m)

# Overlays
for ofile in selected_overlays:
    try:
        ogdf = gpd.read_file(ofile)
        ogdf = to_wgs84(ogdf)
        ogdf = sanitize_for_json(ogdf)
        folium.GeoJson(
            ogdf.to_json(),
            name=f"Overlay: {Path(ofile).name}",
            style_function=lambda x: {
                "color": "#ff7f00",
                "weight": 2,
                "opacity": 0.9,
                "fillOpacity": 0.1,
            },
        ).add_to(m)
    except Exception as e:
        st.toast(f"Failed to load overlay {ofile}: {e}", icon="⚠️")

folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, width=None, height=700)

st.subheader("Data Summary")
st.write(f"Total features loaded: **{len(gdf):,}** | After filters: **{len(filtered):,}**")

with st.expander("Preview filtered attributes"):
    st.dataframe(filtered.drop(columns="geometry").head(100))

# ---- Export (sanitize first) ----
filtered_for_export = sanitize_for_json(filtered)
st.download_button(
    "Download filtered as GeoJSON",
    data=filtered_for_export.to_json(),
    file_name="gcdf_bri_filtered.geojson",
    mime="application/geo+json",
)