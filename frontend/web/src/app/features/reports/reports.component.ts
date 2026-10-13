import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { ApiClientService } from '../../core/api/api-client.service';
import { CoachingReportSummary, PlayerProgressionResponse } from '../../core/api/api-models';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [CommonModule, FormsModule, BentoCardComponent],
  template: `
    <div class="reports-page">
      <app-bento-card span="full" customId="reports-heading">
        <div class="reports-header">
          <div>
            <h1 id="reports-heading" class="page-title">{{ i18n.nav.reports }}</h1>
            <p class="page-subtitle">
              Evaluación táctica multi-agente basada en Match Analyst, Economy Coach, Role Coach y Report Writer.
            </p>
          </div>

          <div class="generate-control">
            <button
              type="button"
              class="btn-primary"
              (click)="onGenerateReport()"
              [disabled]="generating()"
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
            Analiza aperturas de sitio, porcentaje de primeros intercambios (First Bloods) y eficacia en retoma de rondas post-plant.
          </p>
          <div class="agent-stat">
            <span class="stat-num">74%</span>
            <span class="stat-label">Winrate en 5v4 favorable</span>
          </div>
        </app-bento-card>

        <!-- Economy Coach -->
        <app-bento-card title="Economy Coach" subtitle="Gestión de banca y compras de equipo">
          <p class="agent-desc">
            Supervisa la disciplina en rondas semi-eco, fuerza compras sincronizadas y minimiza pérdidas innecesarias de créditos.
          </p>
          <div class="agent-stat">
            <span class="stat-num">89%</span>
            <span class="stat-label">Sincronización con el equipo</span>
          </div>
        </app-bento-card>

        <!-- Role Coach -->
        <app-bento-card title="Role Coach" subtitle="Alineación al rol del agente">
          <p class="agent-desc">
            Optimiza el uso de utilidad táctica, posicionamiento de ancla en defensa y timing de apoyo en ataques coordinados.
          </p>
          <div class="agent-stat">
            <span class="stat-num">A-</span>
            <span class="stat-label">Calificación de impacto de rol</span>
          </div>
        </app-bento-card>

        <!-- Report Writer -->
        <app-bento-card title="Report Writer" subtitle="Síntesis estratégica ejecutable">
          <p class="agent-desc">
            Consolida las métricas de todos los agentes en recomendaciones accionables para tu próxima partida.
          </p>
          <div class="agent-stat">
            <span class="stat-num">3</span>
            <span class="stat-label">Prioridades clave identificadas</span>
          </div>
        </app-bento-card>
      </div>

      <!-- Progression Overview -->
      @if (progression()) {
        <app-bento-card span="full" title="Progresión Táctica Histórica" subtitle="Evolución en el tiempo">
          <div class="progression-container">
            <p><strong>Jugador:</strong> {{ progression()?.game_name }}#{{ progression()?.tag_line }}</p>
            <p><strong>Tendencia global:</strong> {{ progression()?.overall_trend || 'Favorable (+12.4 ACS en las últimas 5 partidas)' }}</p>
          </div>
        </app-bento-card>
      }

      <!-- Reports History -->
      <app-bento-card span="full" title="Historial de Informes Generados" subtitle="Consultas anteriores">
        <ul class="reports-list" role="list">
          @for (r of reports(); track r.id) {
            <li class="report-item">
              <div class="report-info">
                <span class="report-date">{{ r.created_at | date:'dd/MM/yyyy HH:mm' }}</span>
                <h2 class="report-summary-title">{{ r.summary }}</h2>
                <div class="report-points">
                  <span class="tag-strength">Fortalezas: {{ r.strengths }}</span>
                  <span class="tag-weakness">A mejorar: {{ r.weaknesses }}</span>
                </div>
              </div>
            </li>
          } @empty {
            <li class="empty-reports">
              No hay informes guardados aún. Haz clic en "Generar Nuevo Informe" para iniciar la evaluación multi-agente.
            </li>
          }
        </ul>
      </app-bento-card>
    </div>
  `,
  styles: [`
    .reports-page {
      display: flex;
      flex-direction: column;
      gap: var(--main-gap);
    }
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
  readonly i18n = I18N_ES;

  readonly generating = signal(false);
  readonly statusMessage = signal('');
  readonly reports = signal<CoachingReportSummary[]>([
    {
      id: 'report-demo-1',
      created_at: '2026-10-12T20:00:00Z',
      summary: 'Optimización de disciplina económica en compras tempranas y rutas de iniciador.',
      strengths: 'Excelente índice de primeras bajas (78%) y control de mapa en Haven.',
      weaknesses: 'Fuerzas de compra prematuras en rondas 3 tras perder ronda de pistolas.',
    },
  ]);
  readonly progression = signal<PlayerProgressionResponse | null>(null);

  gameName = 'TenZ';
  tagLine = '0001';

  ngOnInit(): void {
    this.loadProgression();
  }

  loadProgression(): void {
    this.api.getPlayerProgression(this.gameName, this.tagLine).subscribe({
      next: (prog) => this.progression.set(prog),
      error: () => {},
    });
  }

  onGenerateReport(): void {
    this.generating.set(true);
    this.statusMessage.set('Iniciando orquestación de agentes especializados...');

    this.api.generateCoachingReport(this.gameName, this.tagLine, 5).subscribe({
      next: (detail) => {
        this.generating.set(false);
        this.statusMessage.set('¡Informe de coaching generado con éxito!');
        if (detail.report) {
          this.reports.update((list) => [
            {
              id: detail.report.id,
              created_at: detail.report.created_at,
              summary: detail.report.summary,
              strengths: detail.report.strengths,
              weaknesses: detail.report.weaknesses,
            },
            ...list,
          ]);
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        this.generating.set(false);
        this.statusMessage.set(
          err?.error?.detail || 'Error al conectar con los agentes de coaching.'
        );
      },
    });
  }
}
