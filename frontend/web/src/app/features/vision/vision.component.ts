import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { ApiClientService } from '../../core/api/api-client.service';
import { VisionAnalysisResponse } from '../../core/api/api-models';

@Component({
  selector: 'app-vision',
  standalone: true,
  imports: [CommonModule, BentoCardComponent],
  template: `
    <div class="vision-page">
      <app-bento-card span="full" customId="vision-title">
        <h1 id="vision-title" class="page-title">{{ i18n.nav.vision }}</h1>
        <p class="page-subtitle">
          Sube una captura de pantalla del marcador de Valorant para extraer estadísticas automáticamente con visión multimodal.
        </p>
      </app-bento-card>

      <app-bento-card span="2" [title]="i18n.bento.uploadCard.title" [subtitle]="i18n.bento.uploadCard.subtitle">
        <div
          class="dropzone"
          [class.dragover]="isDragging()"
          (dragover)="onDragOver($event)"
          (dragleave)="onDragLeave($event)"
          (drop)="onDrop($event)"
        >
          <input
            #fileInput
            id="scoreboard-file"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            class="sr-only"
            (change)="onFileSelected($event)"
            aria-describedby="upload-help"
          />

          <svg
            class="upload-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
          </svg>

          <p class="dropzone-text">{{ i18n.bento.uploadCard.dropzone }}</p>
          <span id="upload-help" class="dropzone-hint">{{ i18n.bento.uploadCard.formats }}</span>

          <button
            type="button"
            class="btn-primary upload-btn"
            (click)="fileInput.click()"
            [disabled]="loading()"
          >
            {{ selectedFileName() ? 'Cambiar archivo' : i18n.bento.uploadCard.button }}
          </button>

          @if (selectedFileName()) {
            <p class="selected-file-info" aria-live="polite">
              Archivo seleccionado: <strong>{{ selectedFileName() }}</strong>
            </p>
          }
        </div>

        @if (selectedFile()) {
          <div class="action-footer">
            <button
              type="button"
              class="btn-primary"
              (click)="analyzeScoreboard()"
              [disabled]="loading()"
            >
              {{ loading() ? 'Analizando captura...' : 'Procesar con IA' }}
            </button>
          </div>
        }

        @if (errorMessage()) {
          <p class="error-msg" role="alert" aria-live="polite">
            {{ errorMessage() }}
          </p>
        }
      </app-bento-card>

      @if (analysisResult()) {
        <app-bento-card span="2" title="Resultado del Análisis de Marcador" subtitle="Datos extraídos por Gemini Vision">
          <div class="result-container" tabindex="0" aria-label="Datos extraídos del marcador">
            <pre class="result-raw">{{ analysisResult() | json }}</pre>
          </div>
        </app-bento-card>
      }
    </div>
  `,
  styles: [`
    .vision-page {
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
    .dropzone {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px 24px;
      border: 2px dashed var(--color-border-dashed);
      border-radius: var(--radius-sm);
      text-align: center;
      gap: 12px;
      transition: border-color var(--transition-fast), background-color var(--transition-fast);
      min-height: 220px;
    }
    .dropzone.dragover {
      border-color: var(--color-primary);
      background-color: rgba(198, 255, 61, 0.05);
    }
    .upload-icon {
      width: 48px;
      height: 48px;
      stroke: var(--color-primary);
    }
    .dropzone-text {
      font-size: 16px;
      font-weight: 500;
    }
    .dropzone-hint {
      font-size: 13px;
      color: var(--color-text-secondary);
    }
    .upload-btn {
      margin-top: 8px;
    }
    .selected-file-info {
      font-size: 14px;
      color: var(--color-primary);
      margin-top: 4px;
    }
    .action-footer {
      display: flex;
      justify-content: flex-end;
      margin-top: 16px;
    }
    .error-msg {
      color: var(--color-loss);
      font-size: 14px;
      margin-top: 12px;
    }
    .result-container {
      background-color: var(--color-bg-page);
      border-radius: var(--radius-sm);
      padding: 16px;
      overflow-x: auto;
      max-height: 400px;
    }
    .result-raw {
      font-family: monospace;
      font-size: 13px;
      color: var(--color-text);
      white-space: pre-wrap;
      word-break: break-all;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class VisionComponent {
  private readonly api = inject(ApiClientService);
  readonly i18n = I18N_ES;

  readonly isDragging = signal(false);
  readonly selectedFile = signal<File | null>(null);
  readonly selectedFileName = signal<string>('');
  readonly loading = signal(false);
  readonly errorMessage = signal<string>('');
  readonly analysisResult = signal<VisionAnalysisResponse | null>(null);

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.handleFile(event.dataTransfer.files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  private handleFile(file: File): void {
    this.errorMessage.set('');
    if (!file.type.startsWith('image/')) {
      this.errorMessage.set('Por favor, selecciona un archivo de imagen válido (PNG, JPG, WEBP).');
      return;
    }
    this.selectedFile.set(file);
    this.selectedFileName.set(file.name);
  }

  analyzeScoreboard(): void {
    const file = this.selectedFile();
    if (!file) return;

    this.loading.set(true);
    this.errorMessage.set('');

    const formData = new FormData();
    formData.append('file', file);

    this.api.postVisionScoreboardAnalyze(formData).subscribe({
      next: (res: VisionAnalysisResponse) => {
        this.loading.set(false);
        this.analysisResult.set(res);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.loading.set(false);
        this.errorMessage.set(err?.error?.detail || 'Error al analizar la captura del marcador.');
      }
    });
  }
}
