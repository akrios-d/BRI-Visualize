import { Injectable } from '@angular/core';

export interface BriProperties {
  id: number;
  Recipient: string;
  'Recipient.ISO-3': string;
  Title: string;
  'Amount.(Constant.USD.2021)': number;
  Status: string;
  'Sector.Name': string;
  'Commitment.Year': number;
}

export interface BriFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: BriProperties;
}

export interface BriCollection {
  type: 'FeatureCollection';
  features: BriFeature[];
}

@Injectable({ providedIn: 'root' })
export class BriService {
  private cache: BriCollection | null = null;

  async loadData(): Promise<BriCollection> {
    if (this.cache) return this.cache;
    const res = await fetch('/data/gcdf_light_simplified.geojson');
    this.cache = (await res.json()) as BriCollection;
    return this.cache;
  }
}
