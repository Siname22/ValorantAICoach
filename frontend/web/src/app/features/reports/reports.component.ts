import { ChangeDetectionStrategy, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, BentoCardComponent],
  template: `
    <div class="reports-page">
      <app-bento-card span="full" [title]="i18n.nav.reports">
        <h1 class="page-title">Informes del Coach</h1>
        <p class="page-subtitle">Evaluación multi-agente de Match Analyst, Economy Coach, Role Coach y Report Writer.</p>
      </app-bento-card>
    </div>
  `,
  styles: [`
    .reports-page {
      display: flex;
      flex-direction: column;
      gap: var(--main-gap);
    }
    .page-title {
      font-size: var(--font-size-h1);
      margin-bottom: 8px;
    }
    .page-subtitle {
      color: var(--color-text-secondary);
      font-size: 14px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReportsComponent {
  readonly i18n = I18N_ES;
}
