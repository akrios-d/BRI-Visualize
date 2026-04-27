import { Injectable } from '@angular/core';
import type { Feature, Point, FeatureCollection } from 'geojson';

export interface BriProperties {
  id: number | null;
  title: string | null;
  recipient: string | null;
  iso3: string | null;
  sector: string | null;
  status: string | null;
  infrastructure: string | null;
  year: number | null;
  completionYear: number | null;
  implYear: number | null;
  amount: number | null;
  dissertationTheme?: string;
}

export type BriFeature = Feature<Point, BriProperties>;
export type BriCollection = FeatureCollection<Point, BriProperties>;
export type DatasetMode = 'full' | 'dissertation';

@Injectable({ providedIn: 'root' })
export class BriService {
  private cache: Record<DatasetMode, BriCollection | null> = { full: null, dissertation: null };

  private readonly urls: Record<DatasetMode, string> = {
    full:         '/data/centroids.json',
    dissertation: '/data/dissertation.json',
  };

  async loadData(mode: DatasetMode): Promise<BriCollection> {
    if (this.cache[mode]) return this.cache[mode]!;
    const res = await fetch(this.urls[mode]);
    this.cache[mode] = (await res.json()) as BriCollection;
    return this.cache[mode]!;
  }
}
