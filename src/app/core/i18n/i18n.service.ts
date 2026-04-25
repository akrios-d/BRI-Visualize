import { Injectable, computed, signal } from '@angular/core';

export type AppLanguage = 'zh' | 'en';

const STORAGE_KEY = 'bri-language';

const LOADED_TRANSLATIONS: Record<AppLanguage, Record<string, string>> = {
  en: {},
  zh: {},
};

const TRANSLATION_LANGS: AppLanguage[] = ['en', 'zh'];

@Injectable({ providedIn: 'root' })
export class I18nService {
  readonly language = signal<AppLanguage>(this.detectInitialLanguage());

  readonly languageOptions = [
    { code: 'en' as const, flag: '🇬🇧' },
    { code: 'zh' as const, flag: '🇨🇳' },
  ];

  readonly appTitle = computed(() => this.t('app.title'));

  loadAll(): Promise<void> {
    const requests = TRANSLATION_LANGS.map((lang) =>
      fetch(`/i18n/${lang}.json`)
        .then((r) => r.json())
        .then((data) => {
          LOADED_TRANSLATIONS[lang] = data;
        })
        .catch(() => {
          // silent fallback
        }),
    );
    return Promise.all(requests).then(() => void 0);
  }

  setLanguage(language: AppLanguage) {
    this.language.set(language);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, language);
    }
  }

  t(key: string): string {
    const lang = this.language();
    const dict = LOADED_TRANSLATIONS[lang] || {};
    const fallback = LOADED_TRANSLATIONS['en'] || {};
    return dict[key] ?? fallback[key] ?? key;
  }

  private detectInitialLanguage(): AppLanguage {
    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'zh' || stored === 'en') return stored;
    }
    if (typeof navigator !== 'undefined') {
      if (navigator.language.toLowerCase().startsWith('zh')) return 'zh';
    }
    return 'en';
  }
}
