import { ChangeDetectionStrategy, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';

@Component({
  selector: 'app-matches',
  standalone: true,
  imports: [CommonModule, BentoCardComponent],
  template: `
    <div class="matches-page">
      <app-bento-card span="full" [title]="i18n.nav.matches">
        <h1 class="page-title">Historial de Partidas</h1>
        <p class="page-subtitle">Telemetría competitiva detallada y análisis ronda por ronda.</p>
      </app-bento-card>
    </div>
  `,
  styles: [`
    .matches-page {
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
export class MatchesComponent {
  readonly i18n = I18N_ES;
}
