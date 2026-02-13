from pathlib import Path
import json
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster, HeatMap
import re

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

    overlays_dir = Path("overlays")
    # Support multiple formats
    overlay_candidates = []
    for ext in (".geojson", ".json", ".shp", ".gpkg"):
        overlay_candidates.extend(sorted(overlays_dir.glob(f"*{ext}")))
    if not overlay_candidates:
        st.caption("Drop .geojson/.json/.shp/.gpkg files in ./overlays to enable overlays.")
    selected_overlays = st.multiselect(
        "Overlay files in ./overlays",
        overlay_candidates,
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

if gdf.empty:
    st.warning("Loaded dataset is empty.")
    st.stop()

# ---------------------------------------------------
# Column detection + Manual override
# ---------------------------------------------------

auto_cols = detect_columns(gdf) or {}
all_cols = ["— None —"] + [c for c in gdf.columns if c != "geometry"]

with st.sidebar:
    st.header("Columns (Auto + Manual Override)")

    # Preselect detected columns if present, else "None"
    def preselect(name):
        v = auto_cols.get(name)
        return v if (isinstance(v, str) and v in gdf.columns) else "— None —"

    col_country   = st.selectbox("Country column",   all_cols, index=all_cols.index(preselect("country")))
    col_sector    = st.selectbox("Sector column",    all_cols, index=all_cols.index(preselect("sector")))
    col_year      = st.selectbox("Year (or date) column", all_cols, index=all_cols.index(preselect("year")))
    col_precision = st.selectbox("Geographic precision column", all_cols, index=all_cols.index(preselect("precision")))
    col_value     = st.selectbox("Value/amount column", all_cols, index=all_cols.index(preselect("value")))

    # Normalize "None" to None
    cols = {
        "country":   None if col_country   == "— None —" else col_country,
        "sector":    None if col_sector    == "— None —" else col_sector,
        "year":      None if col_year      == "— None —" else col_year,
        "precision": None if col_precision == "— None —" else col_precision,
        "value":     None if col_value     == "— None —" else col_value,
    }

# ---------------------------------------------------
# Filters Sidebar
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

    # Helper to produce a numeric year series from many data shapes
    def get_year_series(series: pd.Series) -> pd.Series:
        if series is None:
            return pd.Series([], dtype="float64")

        s = series
        # If already datetime-like
        if pd.api.types.is_datetime64_any_dtype(s):
            return s.dt.year

        # Try datetime parsing from strings/objects
        try:
            dt = pd.to_datetime(s, errors="coerce", utc=True)
            if dt.notna().any():
                return dt.dt.year
        except Exception:
            pass

        # If numeric-like (year as 2020, or 20200101, etc.)
        s_num = pd.to_numeric(s, errors="coerce")
        if s_num.notna().any():
            # Heuristic: if many values > 3000, try to extract 4-digit year
            if (s_num > 3000).mean() > 0.5:
                # Fall back to regex from string
                s_str = s.astype(str)
                yy = s_str.str.extract(r"(\d{4})")[0]
                return pd.to_numeric(yy, errors="coerce")
            return s_num

        # Regex extract last resort
        s_str = s.astype(str)
        yy = s_str.str.extract(r"(\d{4})")[0]
        return pd.to_numeric(yy, errors="coerce")

    # Year filter (robust)
    if cols["year"] and cols["year"] in gdf.columns:
        y_all = get_year_series(gdf[cols["year"]]).dropna().astype(int)
        if not y_all.empty:
            yr_min, yr_max = int(y_all.min()), int(y_all.max())
            sel_min, sel_max = st.slider("Year range", yr_min, yr_max, (yr_min, yr_max))
            year_range = (sel_min, sel_max)
        else:
            year_range = None
            st.info("Year column detected, but could not derive a usable year range from its values.")
    else:
        year_range = None

    # Precision filter
    if cols["precision"] and cols["precision"] in gdf.columns:
        prec_vals = sorted(gdf[cols["precision"]].dropna().astype(str).unique())
        sel_prec = st.multiselect("Geographic precision", prec_vals)
    else:
        sel_prec = []

    # Value bucket
    if cols["value"] and cols["value"] in gdf.columns:
        bucket_choice = st.multiselect("Financing bucket", ["Low", "Medium", "High"])
    else:
        bucket_choice = []

# ---------------------------------------------------
# Apply filters
# ---------------------------------------------------

filtered = gdf.copy()

if sel_countries and cols["country"]:
    filtered = filtered[filtered[cols["country"]].astype(str).isin(sel_countries)]

if sel_sectors and cols["sector"]:
    filtered = filtered[filtered[cols["sector"]].astype(str).isin(sel_sectors)]

if year_range and cols["year"]:
    yy = get_year_series(filtered[cols["year"]])
    filtered = filtered[(yy >= year_range[0]) & (yy <= year_range[1])]

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
# JSON sanitization helper (for Folium/GeoJSON)
# ---------------------------------------------------

def sanitize_for_json(gdf_in: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Ensure all attribute columns are JSON serializable:
    - Convert datetime-like columns to ISO strings.
    - Also convert individual pd.Timestamp values inside object columns.
    """
    gdf = gdf_in.copy()
    for col in gdf.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)
            continue
        if pd.api.types.is_object_dtype(gdf[col]):
            gdf[col] = gdf[col].apply(lambda x: x.isoformat() if isinstance(x, pd.Timestamp) else x)
    return gdf

# ---------------------------------------------------
# Diagnostics (helpful to see what's going on)
# ---------------------------------------------------

with st.expander("🔎 Data diagnostics"):
    st.write("**Detected columns (auto):**", auto_cols)
    st.write("**Columns in use (after manual override):**", cols)
    dtypes = {c: str(gdf[c].dtype) for c in gdf.columns if c != "geometry"}
    st.write("**Attribute dtypes:**", dtypes)
    if cols["year"] and cols["year"] in gdf.columns:
        y_try = get_year_series(gdf[cols["year"]])
        st.write("**First derived years (preview):**", y_try.dropna().astype(int).head(10).tolist())

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
            # If MultiPoint, representative point
            if r.geometry.geom_type == "MultiPoint":
                geom = list(r.geometry.geoms)[0]
                lat, lon = geom.y, geom.x
            else:
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
    heat_data = []
    for _, g in pts.iterrows():
        if g.geometry is None:
            continue
        if g.geometry.geom_type == "Point":
            heat_data.append([g.geometry.y, g.geometry.x])
        elif g.geometry.geom_type == "MultiPoint":
            for p in g.geometry.geoms:
                heat_data.append([p.y, p.x])
    if heat_data:
        HeatMap(heat_data, name="Density heatmap", radius=12, blur=15).add_to(m)

# Overlays
added_overlays = 0
for ofile in selected_overlays:
    try:
        # Read per file type
        if ofile.suffix.lower() in [".geojson", ".json", ".shp"]:
            ogdf = gpd.read_file(ofile)
        elif ofile.suffix.lower() == ".gpkg":
            # Read default/first layer
            ogdf = gpd.read_file(ofile)
        else:
            st.toast(f"Unsupported overlay type: {ofile.name}", icon="⚠️")
            continue

        if ogdf.empty:
            st.toast(f"Overlay {ofile.name} has no features.", icon="⚠️")
            continue

        ogdf = to_wgs84(ogdf)
        ogdf = sanitize_for_json(ogdf)

        folium.GeoJson(
            ogdf.to_json(),
            name=f"Overlay: {ofile.name}",
            style_function=lambda x: {
                "color": "#ff7f00",
                "weight": 2,
                "opacity": 0.9,
                "fillOpacity": 0.1,
            },
        ).add_to(m)
        added_overlays += 1
    except Exception as e:
        st.toast(f"Failed to load overlay {ofile.name}: {e}", icon="⚠️")

folium.LayerControl(collapsed=False).add_to(m)

st_folium(m, width=None, height=700)

# Small heads-up if overlays were selected but none got added
if selected_overlays and added_overlays == 0:
    st.warning("Overlay files were selected but none were added. Check diagnostics or file formats/CRS.")

# ---------------------------------------------------
# Summary + Preview + Export
# ---------------------------------------------------

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