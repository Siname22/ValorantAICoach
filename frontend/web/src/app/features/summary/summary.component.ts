import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { ApiClientService } from '../../core/api/api-client.service';
import {
  PlayerProfile,
  PlayerMatch,
  PlayerStatsOverview,
  CoachingReportSummary,
  PlayerTimelineAnalyticsResponse,
} from '../../core/api/api-models';

@Component({
  selector: 'app-summary',
  standalone: true,
  imports: [CommonModule, FormsModule, BentoCardComponent],
  template: `
    <div class="bento-grid">
      <!-- 1. Hero Card (Full Width): H1 + Search Form (role="search") -->
      <app-bento-card span="full" customId="hero-heading">
        <div class="hero-content">
          <h1 id="hero-heading" class="hero-title">
            {{ i18n.hero.titlePrefix }}
            <span class="highlight-lime">{{ i18n.hero.titleHighlight }}</span>
            {{ i18n.hero.titleSuffix }}
          </h1>

          <form class="hero-search-form" role="search" (ngSubmit)="onSearch()">
            <div class="input-field">
              <label for="riot-id-search" class="input-label">
                {{ i18n.hero.searchLabel }}
              </label>
              <input
                id="riot-id-search"
                type="text"
                name="riotId"
                [(ngModel)]="searchQuery"
                [placeholder]="i18n.hero.searchPlaceholder"
                class="search-input"
                aria-describedby="search-hint"
                required
              />
              <span id="search-hint" class="sr-only">Introduce tu nombre de invocador y lema separados por almohadilla (ej. TenZ#0001).</span>
            </div>

            <button type="submit" class="btn-primary hero-btn" [disabled]="loading()">
              {{ loading() ? i18n.hero.searching : i18n.hero.searchButton }}
            </button>

            @if (playerProfile()) {
              <button
                type="button"
                class="btn-sync"
                (click)="onSync()"
                [disabled]="syncing()"
                aria-label="Sincronizar partidas recientes desde Riot"
              >
                {{ syncing() ? 'Sincronizando...' : '↻ Sincronizar' }}
              </button>
            }
          </form>

          @if (errorMessage()) {
            <p class="search-error" role="alert" aria-live="polite">
              {{ errorMessage() }}
            </p>
          }

          @if (syncMessage()) {
            <p class="sync-status" role="status" aria-live="polite">
              {{ syncMessage() }}
            </p>
          }
        </div>
      </app-bento-card>

      <!-- 2. ACS Medio (Violet #6D3FE0 with white text) -->
      <app-bento-card
        variant="highlight"
        [title]="i18n.bento.acsCard.title"
        [subtitle]="i18n.bento.acsCard.subtitle"
      >
        <div class="metric-display">
          <span class="featured-number">{{ calculatedAcs() }}</span>
          <div class="metric-diff" aria-label="Diferencia frente a la media anterior">
            <span class="diff-tag positive">{{ i18n.bento.acsCard.diffPositive }} (+18.4)</span>
          </div>
        </div>
      </app-bento-card>

      <!-- 3. Plan de Mejora (Ordered list <ol>) -->
      <app-bento-card
        [title]="i18n.bento.planCard.title"
        [subtitle]="i18n.bento.planCard.subtitle"
      >
        @if (latestPlanItems().length > 0) {
          <ol class="plan-list" aria-label="Pasos de mejora recomendados por el coach">
            @for (item of latestPlanItems(); track item.title) {
              <li class="plan-item">
                <strong>{{ item.title }}:</strong> {{ item.description }}
              </li>
            }
          </ol>
        } @else {
          <ol class="plan-list" aria-label="Pasos de mejora recomendados">
            <li class="plan-item">
              <strong>Disciplina en Ronda 3:</strong> Guardar créditos tras derrota para asegurar compra completa en ronda 4.
            </li>
            <li class="plan-item">
              <strong>Distancia de intercambio (&lt;3s):</strong> Mantén línea de visión con el iniciador en B Main.
            </li>
            <li class="plan-item">
              <strong>Conservación de Ultimates:</strong> Evita usar habilidades definitivas en situaciones 4v1 o 5v2.
            </li>
          </ol>
        }
      </app-bento-card>

      <!-- 4. Economía por Ronda (Ambas vistas: Tendencia y Ronda a ronda) -->
      <app-bento-card
        [title]="i18n.bento.economyCard.title"
        [subtitle]="i18n.bento.economyCard.subtitle"
      >
        <div class="economy-container">
          <div class="economy-view-switch" role="tablist" aria-label="Modo de visualización económica">
            <button
              type="button"
              role="tab"
              [attr.aria-selected]="economyMode() === 'trend'"
              id="tab-econ-trend"
              aria-controls="panel-econ-chart"
              class="econ-tab-btn"
              [class.active]="economyMode() === 'trend'"
              (click)="economyMode.set('trend')"
            >
              Tendencia Global
            </button>
            <button
              type="button"
              role="tab"
              [attr.aria-selected]="economyMode() === 'rounds'"
              id="tab-econ-rounds"
              aria-controls="panel-econ-chart"
              class="econ-tab-btn"
              [class.active]="economyMode() === 'rounds'"
              (click)="economyMode.set('rounds')"
            >
              Ronda por Ronda
            </button>
          </div>

          <div id="panel-econ-chart" role="tabpanel" [attr.aria-labelledby]="economyMode() === 'trend' ? 'tab-econ-trend' : 'tab-econ-rounds'">
            @if (economyMode() === 'trend') {
              <!-- Trend SVG Chart -->
              <svg
                class="economy-chart-svg"
                viewBox="0 0 300 80"
                aria-hidden="true"
                focusable="false"
              >
                <polyline
                  fill="none"
                  stroke="var(--color-action-primary)"
                  stroke-width="3"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  points="10,65 50,45 90,60 130,20 170,25 210,55 250,15 290,20"
                />
                <circle cx="10" cy="65" r="4" fill="var(--color-action-primary)" />
                <circle cx="130" cy="20" r="4" fill="var(--color-action-primary)" />
                <circle cx="250" cy="15" r="4" fill="var(--color-action-primary)" />
              </svg>

              <p class="chart-text-description" id="econ-trend-desc">
                {{ i18n.bento.economyCard.chartAccessibleSummary }} <strong>72.5%</strong>. En rondas semi-eco se recomienda priorizar Sheriff/Ghost para no descompensar compras de equipo.
              </p>
            } @else {
              <!-- Round-by-Round SVG Chart -->
              <svg
                class="economy-chart-svg"
                viewBox="0 0 300 80"
                aria-hidden="true"
                focusable="false"
              >
                <polyline
                  fill="none"
                  stroke="var(--color-primary)"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  points="10,30 35,50 60,25 85,70 110,40 135,15 160,20 185,55 210,30 235,20 260,15 285,10"
                />
                <circle cx="85" cy="70" r="4" fill="var(--color-loss)" />
                <circle cx="135" cy="15" r="4" fill="var(--color-win)" />
                <circle cx="285" cy="10" r="4" fill="var(--color-win)" />
              </svg>

              <p class="chart-text-description" id="econ-rounds-desc">
                Análisis de la última partida: Caída económica en ronda 4 tras derrota forzada. Recuperación de banco en ronda 6 (3900 créditos) manteniendo compras completas hasta el cambio de bando (8-4).
              </p>
            }
          </div>
        </div>
      </app-bento-card>

      <!-- 5. Últimas Partidas (Full Width, Semantic Table with Caption, th scope) -->
      <app-bento-card span="full" [title]="i18n.bento.matchesCard.title">
        <div class="table-responsive-container">
          <table aria-describedby="matches-caption">
            <caption id="matches-caption" class="sr-only">{{ i18n.bento.matchesCard.caption }}</caption>
            <thead>
              <tr>
                <th scope="col">{{ i18n.bento.matchesCard.colResult }}</th>
                <th scope="col">{{ i18n.bento.matchesCard.colMap }}</th>
                <th scope="col">{{ i18n.bento.matchesCard.colAgent }}</th>
                <th scope="col">{{ i18n.bento.matchesCard.colScore }}</th>
                <th scope="col">{{ i18n.bento.matchesCard.colKda }}</th>
                <th scope="col">{{ i18n.bento.matchesCard.colAcs }}</th>
              </tr>
            </thead>
            <tbody>
              @if (matches().length > 0) {
                @for (m of matches(); track m.match_id) {
                  <tr>
                    <th scope="row">
                      <span [class.text-victory]="m.result === 'Victory'" [class.text-defeat]="m.result !== 'Victory'">
                        {{ m.result === 'Victory' ? i18n.bento.matchesCard.victory : i18n.bento.matchesCard.defeat }}
                      </span>
                    </th>
                    <td>{{ m.map_name }}</td>
                    <td>{{ m.agent_name }}</td>
                    <td>13 - 9</td>
                    <td>{{ m.kills }} / {{ m.deaths }} / {{ m.assists }}</td>
                    <td>{{ m.score || 240 }}</td>
                  </tr>
                }
              } @else {
                <!-- Default semantic mock row when no search query has been entered yet -->
                <tr>
                  <th scope="row"><span class="text-victory">{{ i18n.bento.matchesCard.victory }}</span></th>
                  <td>Ascent</td>
                  <td>Jett</td>
                  <td>13 - 7</td>
                  <td>22 / 11 / 4</td>
                  <td>284</td>
                </tr>
                <tr>
                  <th scope="row"><span class="text-defeat">{{ i18n.bento.matchesCard.defeat }}</span></th>
                  <td>Haven</td>
                  <td>Sova</td>
                  <td>9 - 13</td>
                  <td>16 / 15 / 9</td>
                  <td>198</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </app-bento-card>

      <!-- 6. Role Coach (Variant Lime) -->
      <app-bento-card
        variant="lime"
        [title]="i18n.bento.roleCoachCard.title"
        [subtitle]="i18n.bento.roleCoachCard.subtitle"
      >
        <div class="role-coach-content">
          <p class="role-summary">
            <strong>Duelista Primario (Jett / Reyna):</strong> Alta eficiencia en entrada y apertura de sitios (78% First Bloods). Se detecta oportunidad de rotación cuando el ancla centinela cae en el sitio opuesto.
          </p>
        </div>
      </app-bento-card>

      <!-- 7. Subida de Marcador (Spans 2 columns, Dashed border, Native button control) -->
      <app-bento-card
        [span]="2"
        [title]="i18n.bento.uploadCard.title"
        [subtitle]="i18n.bento.uploadCard.subtitle"
      >
        <button
          type="button"
          class="upload-zone-btn"
          (click)="fileInput.click()"
          aria-label="Abrir selector para subir captura de pantalla del marcador"
        >
          <input
            #fileInput
            type="file"
            accept="image/png, image/jpeg, image/webp"
            (change)="onFileSelected($event)"
            class="sr-only"
            id="scoreboard-file-upload"
          />
          <div class="upload-prompt" aria-hidden="true">
            <span class="upload-icon">📷</span>
            <span class="upload-text">{{ i18n.bento.uploadCard.subtitle }}</span>
            <span class="upload-subtext">{{ i18n.bento.uploadCard.formats }}</span>
          </div>
          @if (uploadedFileName()) {
            <p class="upload-status" role="status" aria-live="polite">
              Archivo seleccionado: <strong>{{ uploadedFileName() }}</strong>
            </p>
          }
        </button>
      </app-bento-card>
    </div>
  `,
  styles: [`
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: var(--main-gap);
    }

    /* 1. Hero Content */
    .hero-content {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .hero-title {
      font-size: clamp(32px, 5vw, var(--font-size-h1));
      color: var(--color-text-primary);
    }

    .highlight-lime {
      color: var(--color-action-primary);
    }

    .hero-search-form {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: 12px;
    }

    .input-field {
      flex: 1;
      min-width: 280px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .input-label {
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text-secondary);
    }

    .search-input {
      background-color: var(--color-bg-page);
      border: 1px solid var(--color-border-input);
      border-radius: var(--radius-control);
      padding: 0 16px;
      color: var(--color-text-primary);
      min-height: var(--min-touch-target);
      transition: border-color var(--transition-fast);
    }

    .search-input:focus-visible {
      border-color: var(--color-focus);
    }

    .hero-btn {
      min-width: 130px;
    }

    .btn-sync {
      background: transparent;
      border: 1px solid var(--color-border);
      color: var(--color-text);
      font-family: var(--font-body);
      font-size: 14px;
      font-weight: 600;
      padding: 0 16px;
      border-radius: var(--radius-sm);
      min-height: var(--min-touch-target);
      cursor: pointer;
      transition: border-color var(--transition-fast), color var(--transition-fast);
    }

    .btn-sync:hover {
      border-color: var(--color-primary);
      color: var(--color-primary);
    }

    .btn-sync:focus-visible {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
    }

    .search-error {
      color: var(--color-status-defeat);
      font-size: 13px;
    }

    .sync-status {
      color: var(--color-win);
      font-size: 13px;
    }

    /* 2. Metric Display */
    .metric-display {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .featured-number {
      font-family: var(--font-family-display);
      font-size: var(--font-size-featured);
      font-weight: 700;
      line-height: 1;
      color: var(--color-card-highlight-text);
    }

    .diff-tag.positive {
      font-size: 13px;
      font-weight: 600;
      color: #D1BFFF;
    }

    /* 3. Plan List */
    .plan-list {
      padding-left: 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .plan-item {
      font-size: 14px;
      color: var(--color-text-primary);
      line-height: 1.4;
    }

    /* 4. Economy Container */
    .economy-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .economy-view-switch {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--color-border);
      padding-bottom: 6px;
    }

    .econ-tab-btn {
      background: transparent;
      border: none;
      color: var(--color-text-secondary);
      font-size: 13px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: var(--radius-xs);
      cursor: pointer;
      min-height: 36px;
      transition: color var(--transition-fast), background-color var(--transition-fast);
    }

    .econ-tab-btn.active {
      color: var(--color-bg-page);
      background-color: var(--color-primary);
    }

    .econ-tab-btn:focus-visible {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
    }

    .economy-chart-svg {
      width: 100%;
      height: 70px;
      overflow: visible;
    }

    .chart-text-description {
      font-size: 13px;
      color: var(--color-text-secondary);
      line-height: 1.4;
    }

    /* 5. Matches Table Results */
    .text-victory {
      color: var(--color-status-victory);
      font-weight: 700;
    }

    .text-defeat {
      color: var(--color-status-defeat);
      font-weight: 700;
    }

    /* 6. Role Coach Content */
    .role-coach-content {
      font-size: 14px;
      color: var(--color-action-text);
      line-height: 1.5;
    }

    /* 7. Upload Zone Native Button */
    .upload-zone-btn {
      width: 100%;
      background: transparent;
      border: 2px dashed var(--color-border-upload);
      border-radius: var(--radius-control);
      padding: 24px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      cursor: pointer;
      min-height: 120px;
      transition: border-color var(--transition-fast), background-color var(--transition-fast);
      color: inherit;
    }

    .upload-zone-btn:hover {
      border-color: var(--color-action-primary);
      background-color: rgba(198, 255, 61, 0.03);
    }

    .upload-zone-btn:focus-visible {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
      border-color: var(--color-action-primary);
    }

    .upload-prompt {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
    }

    .upload-icon {
      font-size: 28px;
    }

    .upload-text {
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text);
      text-align: center;
    }

    .upload-subtext {
      font-size: 12px;
      color: var(--color-text-secondary);
    }

    .upload-status {
      font-size: 13px;
      color: var(--color-action-primary);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SummaryComponent {
  readonly i18n = I18N_ES;
  private readonly api = inject(ApiClientService);

  searchQuery = 'TenZ#0001';
  readonly loading = signal(false);
  readonly syncing = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly syncMessage = signal<string | null>(null);

  readonly playerProfile = signal<PlayerProfile | null>(null);
  readonly matches = signal<PlayerMatch[]>([]);
  readonly stats = signal<PlayerStatsOverview | null>(null);
  readonly uploadedFileName = signal<string | null>(null);
  readonly economyMode = signal<'trend' | 'rounds'>('trend');
  readonly latestPlanItems = signal<{ title: string; description: string }[]>([]);

  calculatedAcs(): number {
    const s = this.stats();
    if (s && s.kd_ratio) {
      return Math.round(s.kd_ratio * 180);
    }
    return 231;
  }

  onSearch(): void {
    const trimmed = this.searchQuery.trim();
    if (!trimmed || !trimmed.includes('#')) {
      this.errorMessage.set(this.i18n.hero.errorEmpty);
      return;
    }

    this.errorMessage.set(null);
    this.syncMessage.set(null);
    this.loading.set(true);

    const [gameName, tagLine] = trimmed.split('#');
    this.api.getPlayer(gameName, tagLine).subscribe({
      next: (profile: PlayerProfile) => {
        this.playerProfile.set(profile);
        this.loadRecentMatches(gameName, tagLine);
        this.loadStats(gameName, tagLine);
        this.loadCoachingReport(gameName, tagLine);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set(this.i18n.status.notFound);
      },
    });
  }

  onSync(): void {
    const profile = this.playerProfile();
    if (!profile) return;

    this.syncing.set(true);
    this.syncMessage.set(null);

    this.api.syncPlayer(profile.game_name, profile.tag_line).subscribe({
      next: (_res: { status: string; new_report_generated: boolean; report_id?: string }) => {
        this.syncing.set(false);
        this.syncMessage.set('Sincronización completada exitosamente.');
        this.loadRecentMatches(profile.game_name, profile.tag_line);
        this.loadStats(profile.game_name, profile.tag_line);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.syncing.set(false);
        this.syncMessage.set(err?.error?.detail || 'Error al sincronizar partidas.');
      },
    });
  }

  private loadRecentMatches(gameName: string, tagLine: string): void {
    this.api.getPlayerMatches(gameName, tagLine, 5).subscribe({
      next: (res: { matches: PlayerMatch[]; count: number }) => {
        this.matches.set(res.matches || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  private loadStats(gameName: string, tagLine: string): void {
    this.api.getPlayerStats(gameName, tagLine).subscribe({
      next: (st: PlayerStatsOverview) => this.stats.set(st),
      error: () => {},
    });
  }

  private loadCoachingReport(gameName: string, tagLine: string): void {
    this.api.getCoachingReports(gameName, tagLine, 1).subscribe({
      next: (res: { reports: CoachingReportSummary[]; count: number }) => {
        if (res.reports && res.reports.length > 0) {
          const report = res.reports[0];
          if (report.strengths && report.weaknesses) {
            this.latestPlanItems.set([
              { title: 'Fortaleza clave', description: report.strengths.slice(0, 80) },
              { title: 'Área de mejora', description: report.weaknesses.slice(0, 80) },
              { title: 'Recomendación táctica', description: report.summary.slice(0, 80) },
            ]);
          }
        }
      },
      error: () => {},
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.uploadedFileName.set(file.name);
    }
  }
}
