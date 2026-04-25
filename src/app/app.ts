import { Component, HostListener, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { I18nService } from './core/i18n/i18n.service';
import { Flag } from './shared/components/flag/flag';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, Flag],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly i18n = inject(I18nService);
  protected readonly langMenuOpen = signal(false);

  toggleLangMenu(): void {
    this.langMenuOpen.update((v) => !v);
  }

  pickLanguage(code: string): void {
    this.i18n.setLanguage(code as Parameters<typeof this.i18n.setLanguage>[0]);
    this.langMenuOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  closeLangMenu(): void {
    this.langMenuOpen.set(false);
  }
}
