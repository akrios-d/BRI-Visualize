import { Injectable } from '@angular/core';
import type { Feature, Point, FeatureCollection } from 'geojson';

export interface BriProperties {
  id: number | null;
  title: string | null;
  recipient: string | null;
  iso3: string | null;
  sector: string | null;
  status: string | null;
  infrastructure: string | null;   // 'Yes' | null
  year: number | null;
  completionYear: number | null;
  implYear: number | null;
  amount: number | null;           // raw USD
}

export type BriFeature = Feature<Point, BriProperties>;
export type BriCollection = FeatureCollection<Point, BriProperties>;

@Injectable({ providedIn: 'root' })
export class BriService {
  private cache: BriCollection | null = null;

  async loadData(): Promise<BriCollection> {
    if (this.cache) return this.cache;
    const res = await fetch('/data/centroids.json');
    this.cache = (await res.json()) as BriCollection;
    return this.cache;
  }
}
