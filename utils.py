import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List


# ==============================================================
# Column Detection
# ==============================================================

PRECISION_COLS = [
    "geo_precision", "geographic_precision", "precision", "location_precision"
]

COUNTRY_COLS = [
    "country", "recipient_country", "iso3", "country_name"
]

SECTOR_COLS = [
    "sector", "broad_sector_name", "sector_name"
]

YEAR_COLS = [
    "year", "commitment_year", "start_year"
]

VALUE_COLS = [
    "project_value_usd",
    "usd_commitment",
    "commitment_amount_usd",
    "value_usd_2021_const",
]


def detect_columns(gdf: gpd.GeoDataFrame) -> Dict[str, Optional[str]]:
    """
    Case-insensitive column detection.
    Returns actual column names from the GeoDataFrame.
    """
    lower_map = {c.lower(): c for c in gdf.columns}

    def pick(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            if cand in lower_map:
                return lower_map[cand]
        return None

    return {
        "precision": pick(PRECISION_COLS),
        "country": pick(COUNTRY_COLS),
        "sector": pick(SECTOR_COLS),
        "year": pick(YEAR_COLS),
        "value": pick(VALUE_COLS),
    }


# ==============================================================
# CRS Utilities
# ==============================================================

def to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Ensures GeoDataFrame is in EPSG:4326.
    """
    if gdf.crs is None:
        return gdf.set_crs(4326, allow_override=True)

    try:
        if gdf.crs.to_epsg() == 4326:
            return gdf
    except Exception:
        pass

    return gdf.to_crs(4326)


# ==============================================================
# Geometry Simplification
# ==============================================================

def simplify_geometries(
    gdf: gpd.GeoDataFrame,
    tolerance: float = 0.001
) -> gpd.GeoDataFrame:
    """
    Safely simplifies geometries.
    """
    if gdf.empty:
        return gdf

    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(
        tolerance,
        preserve_topology=True
    )
    return gdf


# ==============================================================
# GeoPackage Reader (Robust)
# ==============================================================

def read_geopackage(
    path: Path,
    layer: Optional[str] = None,
    simplify_tol: Optional[float] = None,
) -> gpd.GeoDataFrame:
    """
    Robust GeoPackage reader.
    Tries pyogrio first, then default engine.
    Always returns WGS84 GeoDataFrame.
    """

    if not path or not path.exists():
        raise FileNotFoundError(f"GeoPackage not found: {path}")

    try:
        import pyogrio

        if layer is None:
            layers = [l[0] for l in pyogrio.list_layers(str(path))]
            if not layers:
                raise RuntimeError(f"No layers found in {path}")

            for lyr in layers:
                gdf = gpd.read_file(path, layer=lyr, engine="pyogrio")
                if not gdf.empty:
                    break
        else:
            gdf = gpd.read_file(path, layer=layer, engine="pyogrio")

    except Exception:
        # fallback
        gdf = gpd.read_file(path, layer=layer)

    gdf = to_wgs84(gdf)

    if simplify_tol:
        gdf = simplify_geometries(gdf, simplify_tol)

    return gdf


# ==============================================================
# GeoJSON Folder Reader (Memory-Safe)
# ==============================================================

def read_geojson_folder(
    folder: Path,
    simplify_tol: Optional[float] = None,
) -> gpd.GeoDataFrame:
    """
    Reads all .geojson files in folder and merges safely.
    """

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    files = sorted(folder.glob("*.geojson"))

    if not files:
        raise FileNotFoundError("No .geojson files found")

    frames = []

    for f in files:
        try:
            gdf = gpd.read_file(f)
            frames.append(gdf)
        except Exception as exc:
            print(f"Skipping {f.name}: {exc}")

    if not frames:
        raise RuntimeError("No valid GeoJSON files could be read")

    merged = gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True),
        crs=frames[0].crs
    )

    merged = to_wgs84(merged)

    if simplify_tol:
        merged = simplify_geometries(merged, simplify_tol)

    return merged


# ==============================================================
# JSON-Safe Cleaner (For Folium)
# ==============================================================

def clean_for_json(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts datetime columns to string so Folium won't crash.
    """
    gdf = gdf.copy()

    for col in gdf.columns:
        if col == "geometry":
            continue

        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)

    return gdf
