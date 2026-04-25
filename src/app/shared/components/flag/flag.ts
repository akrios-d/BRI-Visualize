import { Component, input } from '@angular/core';

@Component({
  selector: 'app-flag',
  standalone: true,
  styleUrl: './flag.css',
  template: `
    @switch (lang()) {
      @case ('zh') {
        <svg viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect width="30" height="20" fill="#DE2910"/>
          <polygon fill="#FFDE00" points="7.5,1.5 8.83,4.85 12.4,4.85 9.65,6.88 10.7,10.2 7.5,8.2 4.3,10.2 5.35,6.88 2.6,4.85 6.17,4.85"/>
          <polygon fill="#FFDE00" points="13,0.6 13.5,2.1 15.1,2.1 13.9,3 14.3,4.5 13,3.6 11.7,4.5 12.1,3 10.9,2.1 12.5,2.1"/>
          <polygon fill="#FFDE00" points="15.5,3.6 16,5.1 17.6,5.1 16.4,6 16.8,7.5 15.5,6.6 14.2,7.5 14.6,6 13.4,5.1 15,5.1"/>
          <polygon fill="#FFDE00" points="15.5,7.6 16,9.1 17.6,9.1 16.4,10 16.8,11.5 15.5,10.6 14.2,11.5 14.6,10 13.4,9.1 15,9.1"/>
          <polygon fill="#FFDE00" points="13,10.6 13.5,12.1 15.1,12.1 13.9,13 14.3,14.5 13,13.6 11.7,14.5 12.1,13 10.9,12.1 12.5,12.1"/>
        </svg>
      }
      @default {
        <svg viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect width="30" height="20" fill="#012169"/>
          <line x1="0" y1="0" x2="30" y2="20" stroke="#fff" stroke-width="6"/>
          <line x1="30" y1="0" x2="0" y2="20" stroke="#fff" stroke-width="6"/>
          <line x1="0" y1="0" x2="30" y2="20" stroke="#C8102E" stroke-width="3.5"/>
          <line x1="30" y1="0" x2="0" y2="20" stroke="#C8102E" stroke-width="3.5"/>
          <rect x="12" width="6" height="20" fill="#fff"/>
          <rect y="7" width="30" height="6" fill="#fff"/>
          <rect x="13" width="4" height="20" fill="#C8102E"/>
          <rect y="8" width="30" height="4" fill="#C8102E"/>
        </svg>
      }
    }
  `,
})
export class Flag {
  readonly lang = input.required<string>();
}
