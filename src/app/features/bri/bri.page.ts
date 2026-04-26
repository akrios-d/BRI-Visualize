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

  protected readonly Math = Math;

  private readonly briService = inject(BriService);
  readonly i18n = inject(I18nService);

  readonly loading = signal(true);
  readonly allFeatures = signal<BriFeature[]>([]);
  readonly totalCount = computed(() => this.allFeatures().length);

  // Sector
  readonly selectedSector = signal('');
  readonly sectors = computed(() =>
    [...new Set(this.allFeatures().map(f => f.properties.sector).filter(Boolean) as string[])].sort()
  );

  // Country
  readonly selectedCountry = signal('');
  readonly countries = computed(() =>
    [...new Set(this.allFeatures().map(f => f.properties.recipient).filter(Boolean) as string[])].sort()
  );

  // Status
  readonly selectedStatus = signal('');

  // Infrastructure
  readonly infrastructureOnly = signal(false);

  // Commitment year
  readonly dataCommitYearMin = signal(2000);
  readonly dataCommitYearMax = signal(2021);
  readonly commitYearMin = signal(2000);
  readonly commitYearMax = signal(2021);
  readonly nullCommitYearCount = computed(() =>
    this.allFeatures().filter(f => f.properties.year == null).length
  );
  readonly includeNullCommitYear = signal(true);

  // Completion year
  readonly dataCompletionYearMin = signal(2000);
  readonly dataCompletionYearMax = signal(2023);
  readonly completionYearMin = signal(2000);
  readonly completionYearMax = signal(2023);
  readonly nullCompletionYearCount = computed(() =>
    this.allFeatures().filter(f => f.properties.completionYear == null).length
  );
  readonly includeNullCompletionYear = signal(true);

  // Implementation year
  readonly dataImplYearMin = signal(1996);
  readonly dataImplYearMax = signal(2023);
  readonly implYearMin = signal(1996);
  readonly implYearMax = signal(2023);
  readonly nullImplYearCount = computed(() =>
    this.allFeatures().filter(f => f.properties.implYear == null).length
  );
  readonly includeNullImplYear = signal(true);

  // Amount (stored in USD millions for slider, ×1e6 for filtering)
  readonly dataAmountMax = signal(0);
  readonly amountMin = signal(0);
  readonly amountMax = signal(0);
  readonly nullAmountCount = computed(() =>
    this.allFeatures().filter(f => f.properties.amount == null).length
  );
  readonly includeNullAmount = signal(true);

  // Bucket thresholds (visual color coding only)
  private p33 = 0;
  private p66 = 0;

  private readonly filtered = computed(() => {
    const sector   = this.selectedSector();
    const country  = this.selectedCountry();
    const status   = this.selectedStatus();
    const infraOnly = this.infrastructureOnly();

    const cyMin = this.commitYearMin(),   cyMax = this.commitYearMax();
    const dcyMin = this.dataCommitYearMin(), dcyMax = this.dataCommitYearMax();
    const inclNullCY = this.includeNullCommitYear();
    const cyActive = cyMin > dcyMin || cyMax < dcyMax;

    const cpyMin = this.completionYearMin(), cpyMax = this.completionYearMax();
    const dcpyMin = this.dataCompletionYearMin(), dcpyMax = this.dataCompletionYearMax();
    const inclNullCPY = this.includeNullCompletionYear();
    const cpyActive = cpyMin > dcpyMin || cpyMax < dcpyMax;

    const iyMin = this.implYearMin(), iyMax = this.implYearMax();
    const diyMin = this.dataImplYearMin(), diyMax = this.dataImplYearMax();
    const inclNullIY = this.includeNullImplYear();
    const iyActive = iyMin > diyMin || iyMax < diyMax;

    const aMin = this.amountMin() * 1e6, aMax = this.amountMax() * 1e6;
    const dAMax = this.dataAmountMax() * 1e6;
    const inclNullAmt = this.includeNullAmount();
    const aActive = aMin > 0 || aMax < dAMax;

    return this.allFeatures().filter(f => {
      const p = f.properties;
      if (sector   && p.sector    !== sector)   return false;
      if (country  && p.recipient !== country)  return false;
      if (status   && p.status    !== status)   return false;
      if (infraOnly && p.infrastructure !== 'Yes') return false;

      if (p.year == null) { if (!inclNullCY) return false; }
      else if (cyActive && (p.year < cyMin || p.year > cyMax)) return false;

      if (p.completionYear == null) { if (!inclNullCPY) return false; }
      else if (cpyActive && (p.completionYear < cpyMin || p.completionYear > cpyMax)) return false;

      if (p.implYear == null) { if (!inclNullIY) return false; }
      else if (iyActive && (p.implYear < iyMin || p.implYear > iyMax)) return false;

      if (p.amount == null) { if (!inclNullAmt) return false; }
      else if (aActive && (p.amount < aMin || p.amount > aMax)) return false;

      return true;
    });
  });

  readonly filteredCount = computed(() => this.filtered().length);
  readonly totalAmount = computed(() =>
    this.filtered().reduce((s, f) => s + (f.properties.amount ?? 0), 0)
  );

  readonly hasActiveFilters = computed(() =>
    this.selectedSector()    !== '' ||
    this.selectedCountry()   !== '' ||
    this.selectedStatus()    !== '' ||
    this.infrastructureOnly()         ||
    this.commitYearMin()     >  this.dataCommitYearMin() ||
    this.commitYearMax()     <  this.dataCommitYearMax() ||
    !this.includeNullCommitYear()      ||
    this.completionYearMin() >  this.dataCompletionYearMin() ||
    this.completionYearMax() <  this.dataCompletionYearMax() ||
    !this.includeNullCompletionYear()  ||
    this.implYearMin()       >  this.dataImplYearMin() ||
    this.implYearMax()       <  this.dataImplYearMax() ||
    !this.includeNullImplYear()        ||
    this.amountMin()         >  0     ||
    this.amountMax()         <  this.dataAmountMax() ||
    !this.includeNullAmount()
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
    this.selectedCountry.set('');
    this.selectedStatus.set('');
    this.infrastructureOnly.set(false);
    this.commitYearMin.set(this.dataCommitYearMin());
    this.commitYearMax.set(this.dataCommitYearMax());
    this.includeNullCommitYear.set(true);
    this.completionYearMin.set(this.dataCompletionYearMin());
    this.completionYearMax.set(this.dataCompletionYearMax());
    this.includeNullCompletionYear.set(true);
    this.implYearMin.set(this.dataImplYearMin());
    this.implYearMax.set(this.dataImplYearMax());
    this.includeNullImplYear.set(true);
    this.amountMin.set(0);
    this.amountMax.set(this.dataAmountMax());
    this.includeNullAmount.set(true);
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

  pct(val: number, min: number, max: number): number {
    return ((val - min) / (max - min || 1)) * 100;
  }

  private getBucketColor(amount: number): string {
    if (amount <= this.p33) return BUCKET_COLORS.Low;
    if (amount <= this.p66) return BUCKET_COLORS.Medium;
    return BUCKET_COLORS.High;
  }

  private async loadData(): Promise<void> {
    const data = await this.briService.loadData();
    const feats = data.features;

    const commitYears = feats.map(f => f.properties.year).filter((y): y is number => y != null);
    const compYears   = feats.map(f => f.properties.completionYear).filter((y): y is number => y != null);
    const implYears   = feats.map(f => f.properties.implYear).filter((y): y is number => y != null);
    const amounts     = feats.map(f => f.properties.amount).filter((a): a is number => a != null).sort((a, b) => a - b);

    const cyMin = Math.min(...commitYears), cyMax = Math.max(...commitYears);
    this.dataCommitYearMin.set(cyMin); this.commitYearMin.set(cyMin);
    this.dataCommitYearMax.set(cyMax); this.commitYearMax.set(cyMax);

    const cpyMin = Math.min(...compYears), cpyMax = Math.max(...compYears);
    this.dataCompletionYearMin.set(cpyMin); this.completionYearMin.set(cpyMin);
    this.dataCompletionYearMax.set(cpyMax); this.completionYearMax.set(cpyMax);

    const iyMin = Math.min(...implYears), iyMax = Math.max(...implYears);
    this.dataImplYearMin.set(iyMin); this.implYearMin.set(iyMin);
    this.dataImplYearMax.set(iyMax); this.implYearMax.set(iyMax);

    this.p33 = amounts[Math.floor(amounts.length * 0.33)];
    this.p66 = amounts[Math.floor(amounts.length * 0.66)];
    const maxM = Math.ceil(amounts[amounts.length - 1] / 1e6);
    this.dataAmountMax.set(maxM);
    this.amountMax.set(maxM);

    this.allFeatures.set(feats);
    this.loading.set(false);
  }

  private updateMarkers(features: BriFeature[]): void {
    this.markersLayer!.clearLayers();
    if (!features.length) return;
    const renderer = L.canvas();
    const layer = L.geoJSON({ type: 'FeatureCollection', features } as GeoJSON.FeatureCollection, {
      pointToLayer: (feature, latlng) => {
        const amt = (feature.properties as BriFeature['properties']).amount ?? 0;
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
        const amt = p.amount;
        const color = this.getBucketColor(amt ?? 0);
        const statusClass = (p.status ?? '').toLowerCase().replace(/[^a-z]/g, '-');
        lyr.bindPopup(
          `<div class="bri-popup">
            <div class="popup-title">${p.title ?? '—'}</div>
            <div class="popup-meta">
              <span class="popup-country">${p.recipient ?? '—'}</span>
              <span class="popup-dot">·</span>
              <span>${p.year ?? '—'}</span>
            </div>
            <div class="popup-sector">${p.sector ?? '—'}</div>
            <div class="popup-row">
              <span class="popup-status popup-status--${statusClass}">${p.status ?? '—'}</span>
              <span class="popup-amount" style="color:${color}">${amt != null ? '$' + Math.round(amt).toLocaleString() : '—'}</span>
            </div>
          </div>`,
        );
      },
    });
    this.markersLayer!.addLayer(layer);
  }
}
