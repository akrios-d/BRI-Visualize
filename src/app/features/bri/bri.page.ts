import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { I18nService } from '../../core/i18n/i18n.service';
import { BriFeature, BriService } from './bri.service';
import * as L from 'leaflet';

const BUCKET_COLORS = {
  Low:    '#4a8fc2',
  Medium: '#e08a3c',
  High:   '#c13b2a',
} as const;

@Component({
  selector: 'app-bri-page',
  standalone: true,
  imports: [],
  templateUrl: './bri.html',
  styleUrl: './bri.css',
})
export class BriPage implements AfterViewInit, OnDestroy {
  @ViewChild('mapContainer') mapContainerRef!: ElementRef<HTMLDivElement>;

  private readonly briService = inject(BriService);
  readonly i18n = inject(I18nService);

  readonly loading = signal(true);
  readonly allFeatures = signal<BriFeature[]>([]);

  // Filters
  readonly selectedSector = signal('');
  readonly yearMin = signal(2000);
  readonly yearMax = signal(2021);
  readonly amountMin = signal(0);           // USD millions
  readonly amountMax = signal(0);           // USD millions (set on load)
  readonly selectedStatus = signal('');
  readonly dataAmountMax = signal(0);       // actual max from dataset

  readonly sectors = computed(() =>
    [...new Set(this.allFeatures().map((f) => f.properties['Sector.Name']).filter(Boolean))].sort(),
  );

  // Bucket thresholds (for color coding only, not filtering)
  private p33 = 0;
  private p66 = 0;

  private readonly filtered = computed(() => {
    const sector = this.selectedSector();
    const yMin = this.yearMin();
    const yMax = this.yearMax();
    const aMin = this.amountMin() * 1e6;
    const aMax = this.amountMax() * 1e6;
    const dMax = this.dataAmountMax() * 1e6;
    const status = this.selectedStatus();
    const amountFilterActive = aMin > 0 || aMax < dMax;

    return this.allFeatures().filter((f) => {
      const p = f.properties;
      if (sector && p['Sector.Name'] !== sector) return false;
      const year = p['Commitment.Year'];
      if (year && (year < yMin || year > yMax)) return false;
      if (status && p['Status'] !== status) return false;
      if (amountFilterActive) {
        const amt = p['Amount.(Constant.USD.2021)'] ?? 0;
        if (amt < aMin || amt > aMax) return false;
      }
      return true;
    });
  });

  readonly filteredCount = computed(() => this.filtered().length);

  readonly totalAmount = computed(() =>
    this.filtered().reduce((sum, f) => sum + (f.properties['Amount.(Constant.USD.2021)'] ?? 0), 0),
  );

  readonly hasActiveFilters = computed(
    () =>
      this.selectedSector() !== '' ||
      this.yearMin() !== 2000 ||
      this.yearMax() !== 2021 ||
      this.amountMin() > 0 ||
      this.amountMax() < this.dataAmountMax() ||
      this.selectedStatus() !== '',
  );

  private map: L.Map | null = null;
  private markersLayer: L.LayerGroup | null = null;

  constructor() {
    effect(() => {
      const features = this.filtered();
      if (!this.markersLayer) return;
      this.updateMarkers(features);
    });
  }

  ngAfterViewInit(): void {
    this.map = L.map(this.mapContainerRef.nativeElement).setView([20, 20], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(this.map);
    this.markersLayer = L.layerGroup().addTo(this.map);
    void this.loadData();
  }

  ngOnDestroy(): void {
    this.map?.remove();
    this.map = null;
    this.markersLayer = null;
  }

  resetFilters(): void {
    this.selectedSector.set('');
    this.yearMin.set(2000);
    this.yearMax.set(2021);
    this.amountMin.set(0);
    this.amountMax.set(this.dataAmountMax());
    this.selectedStatus.set('');
  }

  downloadFiltered(): void {
    const collection = { type: 'FeatureCollection', features: this.filtered() };
    const blob = new Blob([JSON.stringify(collection)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'gcdf_filtered.geojson';
    a.click();
    URL.revokeObjectURL(url);
  }

  formatAmount(n: number): string {
    if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
    if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
    return `$${Math.round(n).toLocaleString()}`;
  }

  private getBucketColor(amount: number): string {
    if (amount <= this.p33) return BUCKET_COLORS.Low;
    if (amount <= this.p66) return BUCKET_COLORS.Medium;
    return BUCKET_COLORS.High;
  }

  private async loadData(): Promise<void> {
    const data = await this.briService.loadData();
    const amounts = data.features
      .map((f) => f.properties['Amount.(Constant.USD.2021)'] ?? 0)
      .filter((a) => a > 0)
      .sort((a, b) => a - b);
    this.p33 = amounts[Math.floor(amounts.length * 0.33)];
    this.p66 = amounts[Math.floor(amounts.length * 0.66)];
    const maxM = Math.ceil(amounts[amounts.length - 1] / 1e6);
    this.dataAmountMax.set(maxM);
    this.amountMax.set(maxM);
    this.allFeatures.set(data.features);
    this.loading.set(false);
  }

  private updateMarkers(features: BriFeature[]): void {
    this.markersLayer!.clearLayers();
    if (!features.length) return;
    const renderer = L.canvas();
    const layer = L.geoJSON({ type: 'FeatureCollection', features } as GeoJSON.FeatureCollection, {
      pointToLayer: (feature, latlng) => {
        const amt = (feature.properties as BriFeature['properties'])['Amount.(Constant.USD.2021)'] ?? 0;
        return L.circleMarker(latlng, {
          radius: 5,
          fillColor: this.getBucketColor(amt),
          color: '#fff',
          weight: 1,
          fillOpacity: 0.75,
          renderer,
        });
      },
      onEachFeature: (feature, lyr) => {
        const p = feature.properties as BriFeature['properties'];
        const amt = p['Amount.(Constant.USD.2021)'];
        const color = this.getBucketColor(amt ?? 0);
        lyr.bindPopup(
          `<div class="bri-popup">
            <div class="popup-title">${p['Title'] ?? '—'}</div>
            <div class="popup-meta">
              <span class="popup-country">${p['Recipient'] ?? '—'}</span>
              <span class="popup-dot">·</span>
              <span>${p['Commitment.Year'] ?? '—'}</span>
            </div>
            <div class="popup-sector">${p['Sector.Name'] ?? '—'}</div>
            <div class="popup-row">
              <span class="popup-status popup-status--${(p['Status'] ?? '').toLowerCase().replace(/[^a-z]/g, '-')}">${p['Status'] ?? '—'}</span>
              <span class="popup-amount" style="color:${color}">${amt != null ? '$' + Math.round(amt).toLocaleString() : '—'}</span>
            </div>
          </div>`,
        );
      },
    });
    this.markersLayer!.addLayer(layer);
  }
}
