import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { ApiClientService } from '../../core/api/api-client.service';
import { PlayerProfile, PlayerMatch, PlayerStatsOverview } from '../../core/api/api-models';

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
              <span id="search-hint" class="sr-only">Introduce tu nombre de invocador y lema separados por almohadilla.</span>
            </div>

            <button type="submit" class="btn-primary hero-btn" [disabled]="loading()">
              {{ loading() ? i18n.hero.searching : i18n.hero.searchButton }}
            </button>
          </form>

          @if (errorMessage()) {
            <p class="search-error" role="alert" aria-live="polite">
              {{ errorMessage() }}
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
          <span class="featured-number">{{ stats() ? (stats()!.kd_ratio * 180 | number:'1.0-0') : '231' }}</span>
          <div class="metric-diff" aria-label="Diferencia de rendimiento">
            <span class="diff-tag positive">{{ i18n.bento.acsCard.diffPositive }} (+18.4)</span>
          </div>
        </div>
      </app-bento-card>

      <!-- 3. Plan de Mejora (Ordered list <ol>) -->
      <app-bento-card
        [title]="i18n.bento.planCard.title"
        [subtitle]="i18n.bento.planCard.subtitle"
      >
        <ol class="plan-list" aria-label="Pasos de mejora recomendados">
          <li class="plan-item">
            <strong>Disciplina en Ronda 3:</strong> Guardar créditos tras derrota para asegurar compra completa en ronda 4.
          </li>
          <li class="plan-item">
            <strong>Distancia de intercambio (<3s):</strong> Mantén línea de visión con el iniciador en B Main.
          </li>
          <li class="plan-item">
            <strong>Conservación de Ultimates:</strong> Evita usar habilidades definitivas en superioridad 4v1 o 5v2.
          </li>
        </ol>
      </app-bento-card>

      <!-- 4. Economía por Ronda (Line chart SVG + visible textual description) -->
      <app-bento-card
        [title]="i18n.bento.economyCard.title"
        [subtitle]="i18n.bento.economyCard.subtitle"
      >
        <div class="economy-container">
          <!-- Accessible SVG Chart (aria-hidden because visible text provides full alternative) -->
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

          <!-- Requirement 15: Visible text alternative explaining the trend -->
          <p class="chart-text-description" id="econ-trend-desc">
            {{ i18n.bento.economyCard.chartAccessibleSummary }} <strong>72.5%</strong>. En rondas semi-eco se recomienda priorizar Sheriff/Ghost para no descompensar compras de equipo.
          </p>
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
            <strong>Duelista Primario (Jett / Reyna):</strong> Alta eficiencia en entrada y apertura de sitios (78% First Bloods). Se detecta falta de rotación cuando el ancla centinela cae en el sitio opuesto.
          </p>
        </div>
      </app-bento-card>

      <!-- 7. Subida de Marcador (Spans 2 columns, Dashed border) -->
      <app-bento-card
        [span]="2"
        [title]="i18n.bento.uploadCard.title"
        [subtitle]="i18n.bento.uploadCard.subtitle"
      >
        <div class="upload-zone" (click)="fileInput.click()" (keydown.enter)="fileInput.click()" tabindex="0" role="button" aria-label="Subir captura de marcador">
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
          </div>
          @if (uploadedFileName()) {
            <p class="upload-status" role="status" aria-live="polite">
              Archivo seleccionado: <strong>{{ uploadedFileName() }}</strong>
            </p>
          }
        </div>
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

    .search-error {
      color: var(--color-status-defeat);
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

    /* 7. Upload Zone */
    .upload-zone {
      border: 2px dashed var(--color-border-upload);
      border-radius: var(--radius-control);
      padding: 32px 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      cursor: pointer;
      transition: border-color var(--transition-fast), background-color var(--transition-fast);
      min-height: 120px;
    }

    .upload-zone:hover,
    .upload-zone:focus-visible {
      border-color: var(--color-action-primary);
      background-color: rgba(198, 255, 61, 0.03);
    }

    .upload-icon {
      font-size: 28px;
    }

    .upload-text {
      font-size: 13px;
      color: var(--color-text-secondary);
      text-align: center;
    }

    .upload-status {
      font-size: 13px;
      color: var(--color-action-primary);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SummaryComponent {
  readonly i18n = I18N_ES;
  private readonly api = inject(ApiClientService);

  searchQuery = 'TenZ#0001';
  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly playerProfile = signal<PlayerProfile | null>(null);
  readonly matches = signal<PlayerMatch[]>([]);
  readonly stats = signal<PlayerStatsOverview | null>(null);
  readonly uploadedFileName = signal<string | null>(null);

  onSearch(): void {
    const trimmed = this.searchQuery.trim();
    if (!trimmed || !trimmed.includes('#')) {
      this.errorMessage.set(this.i18n.hero.errorEmpty);
      return;
    }

    this.errorMessage.set(null);
    this.loading.set(true);

    const [gameName, tagLine] = trimmed.split('#');
    this.api.getPlayer(gameName, tagLine).subscribe({
      next: (profile) => {
        this.playerProfile.set(profile);
        this.loadRecentMatches(gameName, tagLine);
        this.loadStats(gameName, tagLine);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set(this.i18n.status.notFound);
      }
    });
  }

  private loadRecentMatches(gameName: string, tagLine: string): void {
    this.api.getPlayerMatches(gameName, tagLine, 5).subscribe({
      next: (res) => {
        this.matches.set(res.matches || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  private loadStats(gameName: string, tagLine: string): void {
    this.api.getPlayerStats(gameName, tagLine).subscribe({
      next: (st) => this.stats.set(st),
      error: () => {}
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
