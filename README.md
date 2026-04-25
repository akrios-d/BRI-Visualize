# BRI Visualize

A web app to explore **AidData's Geospatial Global Chinese Development Finance (GeoGCDF v3)** dataset — 9,405 projects across 148 countries from 2000 to 2021.

Built with Angular 21, Leaflet, and Vercel. Available in English and Chinese (中文).

## Getting started

```bash
npm install
npm start        # http://localhost:4200
```

## Deploy (Vercel)

Push to your repo — `vercel.json` handles SPA routing automatically. No backend required.

## Features

- Interactive global map (Leaflet) with canvas rendering for performance
- Filters: sector, year range, financing level (Low / Medium / High)
- Download filtered subset as GeoJSON
- EN / ZH language switching

## Project structure

```
src/
  app/
    core/i18n/          ← i18n service (EN + ZH, signal-based)
    shared/components/  ← Flag component
    features/bri/       ← map page (bri.page.ts + bri.service.ts)
  styles.css            ← design tokens
public/
  i18n/en.json
  i18n/zh.json
  data/gcdf_light_simplified.geojson   ← 4.1MB, 9,405 point features
```

## Data

`public/data/gcdf_light_simplified.geojson` is derived from AidData's GeoGCDF v3 dataset. Polygon geometries were converted to centroids for web performance. Original data files (`.gpkg`, full GeoJSONs) remain in `data/` for reference.

## Data sources

- [AidData GeoGCDF v3](https://www.aiddata.org/data/geocoded-chinese-global-official-finance-dataset-version-3-0)
- AidData blog on the GeoGCDF v3 release
- Scientific Data open-access article describing methods and coverage
