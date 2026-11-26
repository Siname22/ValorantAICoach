import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { ApiClientService } from '../../core/api/api-client.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import {
  CoachingReportDetailResponse,
  CoachingReportSummary,
  PlayerProgressionResponse,
} from '../../core/api/api-models';

/** Normalizes a stored report (flat fields or orchestrator payload) into a list item. */
type ReportLike = Pick<CoachingReportSummary, 'id' | 'created_at' | 'summary' | 'strengths' | 'weaknesses' | 'payload'>;

export function toReportSummary(rep: ReportLike): CoachingReportSummary {
  const payload = rep.payload || {};
  const join = (v: unknown): string => (Array.isArray(v) ? v.join('. ') : v ? String(v) : '');
  return {
    id: rep.id,
    created_at: rep.created_at,
    summary: String(
      rep.summary || payload['executive_summary'] || payload['summary'] || 'Informe táctico'
    ),
    strengths: rep.strengths || join(payload['key_strengths'] ?? payload['strengths']),
    weaknesses: rep.weaknesses || join(payload['critical_flaws'] ?? payload['weaknesses']),
  };
}

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, BentoCardComponent],
  template: `
    <div class="reports-page">
      <app-bento-card span="full" customId="reports-heading">
        <div class="reports-header">
          <div>
            <h1 id="reports-heading" class="page-title">{{ i18n.nav.reports }}</h1>
            <p class="page-subtitle">
              Evaluación táctica multi-agente basada en Match Analyst, Economy Coach, Role Coach y Report Writer.
            </p>
            @if (player(); as p) {
              <p class="active-player" data-testid="active-player">
                Jugador: <strong>{{ p.gameName }}#{{ p.tagLine }}</strong> · Región {{ p.region | uppercase }}
              </p>
            }
          </div>

          <div class="generate-control">
            <button
              type="button"
              class="btn-primary"
              (click)="onGenerateReport()"
              [disabled]="generating() || !player()"
            >
              {{ generating() ? 'Generando análisis IA...' : '⚡ Generar Nuevo Informe' }}
            </button>
          </div>
        </div>

        @if (statusMessage()) {
          <p class="status-msg" role="status" aria-live="polite">
            {{ statusMessage() }}
          </p>
        }
      </app-bento-card>

      <!-- 4 Specialized Agents Overview Cards Grid -->
      <div class="agents-grid">
        <!-- Match Analyst -->
        <app-bento-card title="Match Analyst" subtitle="Patrones tácticos y duelismo">
          <p class="agent-desc">
            Describe aperturas de sitio, primeros intercambios (First Bloods) y retomas post-plant cuando hay datos suficientes.
          </p>
        </app-bento-card>

        <!-- Economy Coach -->
        <app-bento-card title="Economy Coach" subtitle="Gestión de banca y compras de equipo">
          <p class="agent-desc">
            Supervisa la disciplina en rondas semi-eco, fuerza compras sincronizadas y minimiza pérdidas innecesarias de créditos.
          </p>
        </app-bento-card>

        <!-- Role Coach -->
        <app-bento-card title="Role Coach" subtitle="Alineación al rol del agente">
          <p class="agent-desc">
            Optimiza el uso de utilidad táctica, posicionamiento de ancla en defensa y timing de apoyo en ataques coordinados.
          </p>
        </app-bento-card>

        <!-- Report Writer -->
        <app-bento-card title="Report Writer" subtitle="Síntesis estratégica ejecutable">
          <p class="agent-desc">
            Consolida las métricas de todos los agentes en recomendaciones accionables para tu próxima partida.
          </p>
        </app-bento-card>
      </div>

      <!-- Progression Overview -->
      @if (progression()) {
        <app-bento-card span="full" title="Progresión Táctica Histórica" subtitle="Evolución en el tiempo">
          <div class="progression-container">
            <p><strong>Jugador:</strong> {{ progression()?.game_name }}#{{ progression()?.tag_line }}</p>
            <p><strong>Tendencia global:</strong> {{ progression()?.trajectory_narrative || progression()?.overall_trend || 'Sin datos de tendencia suficientes.' }}</p>
          </div>
        </app-bento-card>
      }

      <!-- Reports History -->
      <app-bento-card span="full" title="Historial de Informes Generados" subtitle="Consultas anteriores">
        @if (!player()) {
          <p class="empty-reports" role="status" data-testid="no-player">
            Aún no has seleccionado un jugador.
            <a routerLink="/resumen">Busca un Riot ID en Resumen</a> para ver sus informes.
          </p>
        } @else if (loadingHistory()) {
          <p class="empty-reports" role="status" data-testid="loading">Cargando historial de informes...</p>
        } @else if (historyError()) {
          <div class="empty-reports" role="alert" data-testid="history-error">
            <p>{{ historyError() }}</p>
            <button type="button" class="btn-primary" (click)="loadHistory()">Reintentar</button>
          </div>
        } @else {
        <ul class="reports-list" role="list">
          @for (r of reports(); track r.id) {
            <li class="report-item">
              <div class="report-info">
                <span class="report-date">{{ r.created_at | date:'dd/MM/yyyy HH:mm' }}</span>
                <h2 class="report-summary-title">{{ r.summary }}</h2>
                <div class="report-points">
                  @if (r.strengths) {
                    <span class="tag-strength">Fortalezas: {{ r.strengths }}</span>
                  }
                  @if (r.weaknesses) {
                    <span class="tag-weakness">A mejorar: {{ r.weaknesses }}</span>
                  }
                </div>
              </div>
            </li>
          } @empty {
            <li class="empty-reports" data-testid="empty-history">
              No hay informes guardados para este jugador y región. Los informes antiguos sin región no aparecen aquí.
            </li>
          }
        </ul>
        }
      </app-bento-card>
    </div>
  `,
  styles: [`
    .reports-page {
      display: flex;
      flex-direction: column;
      gap: var(--main-gap);
    }
    .active-player { font-size: 14px; margin-top: 4px; }
    .reports-header {
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
    .status-msg {
      margin-top: 12px;
      color: var(--color-primary);
      font-size: 14px;
      font-weight: 500;
    }
    .agents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: var(--main-gap);
    }
    .agent-desc {
      font-size: 14px;
      color: var(--color-text-secondary);
      line-height: 1.5;
      margin-bottom: 16px;
    }
    .agent-stat {
      display: flex;
      flex-direction: column;
      gap: 4px;
      border-top: 1px solid var(--color-border);
      padding-top: 12px;
    }
    .stat-num {
      font-family: var(--font-heading);
      font-size: 28px;
      font-weight: 700;
      color: var(--color-primary);
    }
    .stat-label {
      font-size: 12px;
      color: var(--color-text-secondary);
    }
    .progression-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 15px;
    }
    .reports-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .report-item {
      background-color: var(--color-bg-page);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 18px 20px;
    }
    .report-info {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .report-date {
      font-size: 12px;
      color: var(--color-text-secondary);
    }
    .report-summary-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-text);
      margin: 0;
    }
    .report-points {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 6px;
      font-size: 13px;
    }
    .tag-strength {
      color: var(--color-win);
    }
    .tag-weakness {
      color: var(--color-loss);
    }
    .empty-reports {
      color: var(--color-text-secondary);
      padding: 24px 0;
      text-align: center;
      font-size: 14px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReportsComponent implements OnInit {
  private readonly api = inject(ApiClientService);
  private readonly activePlayer = inject(ActivePlayerService);
  readonly i18n = I18N_ES;

  readonly player = this.activePlayer.player;
  readonly generating = signal(false);
  readonly statusMessage = signal('');
  readonly reports = signal<CoachingReportSummary[]>([]);
  readonly loadingHistory = signal(false);
  readonly historyError = signal<string | null>(null);
  readonly progression = signal<PlayerProgressionResponse | null>(null);

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    const p = this.activePlayer.player();
    const version = this.activePlayer.version();
    this.reports.set([]);
    this.progression.set(null);
    this.historyError.set(null);
    if (!p) return;

    this.loadingHistory.set(true);
    this.api.getCoachingReports(p.gameName, p.tagLine, 20, p.region).subscribe({
      next: (res: { reports: CoachingReportSummary[]; count: number }) => {
        if (!this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.reports.set((res.reports || []).map(toReportSummary));
        this.loadingHistory.set(false);
        this.loadProgression(version);
      },
      error: () => {
        if (!this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.loadingHistory.set(false);
        this.historyError.set(
          'No se pudo cargar el historial de informes de ' +
            p.gameName + '#' + p.tagLine + '. No se muestran informes de ejemplo.'
        );
      },
    });
  }

  loadProgression(version = this.activePlayer.version()): void {
    const p = this.activePlayer.player();
    if (!p) return;
    this.api.getPlayerProgression(p.gameName, p.tagLine, p.region).subscribe({
      next: (prog: PlayerProgressionResponse) => {
        if (this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) this.progression.set(prog);
      },
      error: () => {
        // Progression is optional; absence is shown as "no data".
      },
    });
  }

  onGenerateReport(): void {
    const p = this.activePlayer.player();
    if (!p) return;
    const version = this.activePlayer.version();
    this.generating.set(true);
    this.statusMessage.set('Iniciando orquestación de agentes especializados...');

    this.api.generateCoachingReport(p.gameName, p.tagLine, 5, p.region).subscribe({
      next: (detail: CoachingReportDetailResponse) => {
        if (!this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.generating.set(false);
        if (detail && detail.id && detail.payload) {
          this.statusMessage.set('¡Informe de coaching generado con éxito!');
          const item = toReportSummary(detail);
          this.reports.update((list) => [item, ...list.filter((r) => r.id !== item.id)]);
          this.loadProgression(version);
        } else {
          this.statusMessage.set('El servidor no devolvió un informe. No hay datos suficientes todavía.');
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        if (!this.activePlayer.isCurrent(p.gameName, p.tagLine, p.region, version)) return;
        this.generating.set(false);
        this.statusMessage.set(
          err?.error?.detail || 'Error al conectar con los agentes de coaching.'
        );
      },
    });
  }
}
