import { ChangeDetectionStrategy, Component } from '@angular/core';
import { I18N_ES } from '../../../core/i18n/es';

@Component({
  selector: 'app-skip-link',
  standalone: true,
  template: `
    <a href="#main-content" class="skip-link" (click)="onSkipToContent($event)">
      {{ text }}
    </a>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SkipLinkComponent {
  readonly text = I18N_ES.app.skipLink;

  onSkipToContent(event: MouseEvent): void {
    event.preventDefault();
    const mainEl = document.getElementById('main-content');
    if (mainEl) {
      if (!mainEl.hasAttribute('tabindex')) {
        mainEl.setAttribute('tabindex', '-1');
      }
      mainEl.focus();
      mainEl.scrollIntoView({ behavior: 'smooth' });
    }
  }
}
