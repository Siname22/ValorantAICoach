import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { ApiClientService } from '../../core/api/api-client.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import { MatchTimelineResponse, PlayerMatch } from '../../core/api/api-models';

@Component({
  selector: 'app-matches',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, BentoCardComponent],
  template: `
    <div class="matches-page">
      <app-bento-card span="full" customId="matches-heading">
        <div class="matches-header">
          <div>
            <h1 id="matches-heading" class="page-title">{{ i18n.nav.matches }}</h1>
            <p class="page-subtitle">
              Historial completo de partidas competitivas y telemetría por ronda.
            </p>
            @if (player(); as p) {
              <p class="active-player" data-testid="active-player">
                Jugador: <strong>{{ p.gameName }}#{{ p.tagLine }}</strong> · Región {{ p.region | uppercase }}
              </p>
            }
          </div>

          <!-- Filter Controls -->
          <div class="filter-controls" role="group" aria-label="Filtros de historial de partidas">
            <label for="filter-result" class="filter-label">Resultado:</label>
            <select
              id="filter-result"
              [(ngModel)]="filterResult"
              (change)="applyFilter()"
              class="filter-select"
            >
              <option value="all">Todas</option>
              <option value="Victory">Solo Victorias</option>
              <option value="Defeat">Solo Derrotas</option>
            </select>
          </div>
        </div>
      </app-bento-card>

      @if (!player()) {
        <app-bento-card span="full">
          <p class="state-msg" role="status" data-testid="no-player">
            Aún no has seleccionado un jugador.
            <a routerLink="/resumen">Busca un Riot ID en Resumen</a> para ver sus partidas.
          </p>
        </app-bento-card>
      } @else if (loading()) {
        <app-bento-card span="full">
          <p class="state-msg" role="status" data-testid="loading">Cargando partidas...</p>
        </app-bento-card>
      } @else if (loadError()) {
        <app-bento-card span="full">
          <p class="state-msg state-error" role="alert" data-testid="load-error">
            {{ loadError() }}
          </p>
          <button type="button" class="btn-primary" (click)="loadMatches()">Reintentar</button>
        </app-bento-card>
      } @else {
      <!-- Matches Table Card -->
      <app-bento-card span="full" title="Partidas Recientes" subtitle="Últimas partidas disputadas">
        <div class="table-responsive-container">
          <table aria-describedby="matches-history-caption">
            <caption id="matches-history-caption" class="sr-only">
              Tabla con el registro de partidas recientes, mostrando resultado, mapa, agente, marcador, KDA y ACS.
            </caption>
            <thead>
              <tr>
                <th scope="col">Resultado</th>
                <th scope="col">Mapa</th>
                <th scope="col">Agente</th>
                <th scope="col">Marcador</th>
                <th scope="col">K / D / A</th>
                <th scope="col">Puntuación / ACS</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              @for (m of filteredMatches(); track m.match_id) {
                <tr>
                  <th scope="row">
                    <span [class.text-victory]="m.result === 'Victory'" [class.text-defeat]="m.result !== 'Victory'">
                      {{ m.result === 'Victory' ? '▲ Victoria' : '▼ Derrota' }}
                    </span>
                  </th>
                  <td>{{ m.map_name }}</td>
                  <td>{{ m.agent_name }}</td>
                  <td>{{ m.round_score || '—' }}</td>
                  <td>{{ m.kills }} / {{ m.deaths }} / {{ m.assists }}</td>
                  <td>{{ m.score !== null && m.score !== undefined ? m.score : '—' }}</td>
                  <td>
                    <button
                      type="button"
                      class="btn-timeline"
                      (click)="inspectTimeline(m.match_id)"
                      [attr.aria-label]="'Inspeccionar rondas de la partida en ' + m.map_name"
                    >
                      Ver rondas
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7" class="empty-state">
                    {{ allMatches().length === 0
                      ? 'No hay partidas registradas para este jugador. Sincroniza desde Resumen.'
                      : 'No hay partidas que coincidan con los filtros seleccionados.' }}
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </app-bento-card>

      @if (timelineError()) {
        <app-bento-card span="full">
          <p class="state-msg state-error" role="alert" data-testid="timeline-error">
            {{ timelineError() }}
          </p>
        </app-bento-card>
      }
      @if (timelineLoading()) {
        <app-bento-card span="full">
          <p class="state-msg" role="status">Cargando rondas...</p>
        </app-bento-card>
      }

      <!-- Match Timeline Detail (when selected) -->
      @if (selectedTimeline()) {
        <app-bento-card span="full" title="Desglose Ronda por Ronda" subtitle="Línea temporal táctica">
          <div class="timeline-detail-container">
            <div class="timeline-summary">
              <p><strong>Partida:</strong> {{ selectedMatchId() }}</p>
              <p><strong>Rondas registradas:</strong> {{ selectedTimeline()?.rounds?.length || 0 }}</p>
            </div>

            <div class="rounds-grid">
              @for (r of selectedTimeline()?.rounds; track r.round_number) {
                <div class="round-card" [class.round-won]="r.result === 'Won'" [class.round-lost]="r.result !== 'Won'">
                  <div class="round-header">
                    <span class="round-num">Ronda {{ r.round_number }}</span>
                    <span class="round-result">{{ r.result === 'Won' ? '▲ Victoria' : '▼ Derrota' }}</span>
                  </div>
                  <div class="round-body">
                    <p class="round-metric">Banca: {{ r.loadout_value }} creds</p>
                    <p class="round-metric">Gasto: {{ r.spent_credits }} creds</p>
                  </div>
                </div>
              }
            </div>

            <button type="button" class="btn-primary close-timeline-btn" (click)="closeTimeline()">
              Cerrar desglose
            </button>
          </div>
        </app-bento-card>
      }
      }
    </div>
  `,
  styles: [`
    .matches-page {
      display: flex;
      flex-direction: column;
      gap: var(--main-gap);
    }
    .matches-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }
    .page-title {
      font-size: var(--font-size-h1);
      margin-bottom: 8px;
    }
    .page-subtitle {
      color: var(--color-text-secondary);
      font-size: 14px;
    }
    .active-player { font-size: 14px; margin-top: 4px; }
    .state-msg { color: var(--color-text-secondary); font-size: 14px; padding: 12px 0; }
    .state-error { color: var(--color-loss); }
    .filter-controls {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .filter-label {
      font-size: 14px;
      color: var(--color-text-secondary);
    }
    .filter-select {
      background-color: var(--color-bg-page);
      border: 1px solid var(--color-input-border);
      color: var(--color-text);
      font-family: var(--font-body);
      font-size: 14px;
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      min-height: 44px;
      cursor: pointer;
    }
    .filter-select:focus-visible {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
    }
    .btn-timeline {
      background: transparent;
      border: 1px solid var(--color-primary);
      color: var(--color-primary);
      font-size: 13px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: var(--radius-xs);
      cursor: pointer;
      min-height: 44px;
      transition: background-color var(--transition-fast), color var(--transition-fast);
    }
    .btn-timeline:hover {
      background-color: var(--color-primary);
      color: var(--color-bg-page);
    }
    .btn-timeline:focus-visible {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
    }
    .empty-state {
      text-align: center;
      padding: 32px 16px;
      color: var(--color-text-secondary);
    }
    .text-victory {
      color: var(--color-win);
      font-weight: 700;
    }
    .text-defeat {
      color: var(--color-loss);
      font-weight: 700;
    }
    .timeline-detail-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .timeline-summary {
      display: flex;
      gap: 24px;
      font-size: 15px;
    }
    .rounds-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 10px;
    }
    .round-card {
      background-color: var(--color-bg-page);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .round-card.round-won {
      border-left: 4px solid var(--color-win);
    }
    .round-card.round-lost {
      border-left: 4px solid var(--color-loss);
    }
    .round-header {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      font-weight: 600;
    }
    .round-metric {
      font-size: 11px;
      color: var(--color-text-secondary);
      margin: 2px 0;
    }
    .close-timeline-btn {
      align-self: flex-start;
      margin-top: 8px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MatchesComponent implements OnInit {
  private readonly api = inject(ApiClientService);
  private readonly activePlayer = inject(ActivePlayerService);
  readonly i18n = I18N_ES;

  readonly player = this.activePlayer.player;
  readonly allMatches = signal<PlayerMatch[]>([]);
  readonly loading = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly filteredMatches = signal<PlayerMatch[]>([]);
  readonly selectedTimeline = signal<MatchTimelineResponse | null>(null);
  readonly selectedMatchId = signal<string | null>(null);
  readonly timelineLoading = signal(false);
  readonly timelineError = signal<string | null>(null);
  filterResult = 'all';

  ngOnInit(): void {
    this.loadMatches();
  }

  loadMatches(): void {
    const p = this.activePlayer.player();
    const version = this.activePlayer.version();
    this.allMatches.set([]);
    this.filteredMatches.set([]);
    this.closeTimeline();
    this.loadError.set(null);
    if (!p) return;

    this.loading.set(true);
    this.api.getPlayerMatches(p.gameName, p.tagLine, 20, p.region).subscribe({
      next: (res: { matches: PlayerMatch[]; count: number }) => {
        if (!this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.allMatches.set(res.matches || []);
        this.applyFilter();
        this.loading.set(false);
      },
      error: () => {
        if (!this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.loading.set(false);
        this.loadError.set(
          'No se pudieron cargar las partidas de ' +
            p.gameName + '#' + p.tagLine +
            '. Inténtalo de nuevo; no se muestran datos de ejemplo.'
        );
      },
    });
  }

  applyFilter(): void {
    const all = this.allMatches();
    if (this.filterResult === 'all') {
      this.filteredMatches.set(all);
    } else {
      this.filteredMatches.set(all.filter((m) => m.result === this.filterResult));
    }
  }

  inspectTimeline(matchId: string): void {
    const p = this.activePlayer.player();
    if (!p) return;
    const version = this.activePlayer.version();
    this.selectedMatchId.set(matchId);
    this.selectedTimeline.set(null);
    this.timelineError.set(null);
    this.timelineLoading.set(true);
    this.api.getMatchTimeline(matchId).subscribe({
      next: (tl: MatchTimelineResponse) => {
        if (this.selectedMatchId() !== matchId || !this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.timelineLoading.set(false);
        if (!tl.rounds || tl.rounds.length === 0) {
          this.timelineError.set('Esta partida no tiene desglose por rondas disponible.');
          return;
        }
        this.selectedTimeline.set(tl);
      },
      error: () => {
        if (this.selectedMatchId() !== matchId || !this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.timelineLoading.set(false);
        this.timelineError.set(
          'No se pudo cargar el desglose por rondas de esta partida. No se muestran datos de ejemplo.'
        );
      },
    });
  }

  closeTimeline(): void {
    this.selectedTimeline.set(null);
    this.selectedMatchId.set(null);
    this.timelineError.set(null);
    this.timelineLoading.set(false);
  }
}
