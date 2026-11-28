import { ChangeDetectionStrategy, Component, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { TokenService } from '../../core/auth/token.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import { ChatSessionService } from './chat-session.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, BentoCardComponent],
  template: `
    <section class="chat-page" aria-labelledby="chat-title">
      <app-bento-card span="full">
        <div class="heading">
          <div>
            <h1 id="chat-title">AI Coach</h1>
            <p>Entrenamiento práctico para tu próxima partida.</p>
            @if (active.player(); as player) {
              <p class="context">Contexto: {{ player.gameName }}#{{ player.tagLine }} · {{ player.region | uppercase }}</p>
            } @else {
              <p class="context">Sin jugador seleccionado. Puedes hacer preguntas generales.</p>
            }
          </div>
          <button type="button" class="btn-secondary" (click)="reset()" [disabled]="!session.messages().length && !session.error() && !draft">Reiniciar chat</button>
        </div>
      </app-bento-card>

      <app-bento-card span="full" title="Conversación" subtitle="Respuestas del coach con contexto verificado">
        @if (!session.messages().length) {
          <p>Pregunta por economía, posicionamiento o decisiones de ronda.</p>
          <div class="starters" aria-label="Preguntas iniciales">
            @for (starter of starters; track starter) {
              <button type="button" class="starter" (click)="ask(starter)" [disabled]="session.loading()">{{ starter }}</button>
            }
          </div>
        }
        <ol class="messages" aria-label="Mensajes del chat" aria-live="polite">
          @for (message of session.messages(); track $index) {
            <li [class.assistant]="message.role === 'assistant'">
              <strong>{{ message.role === 'assistant' ? 'AI Coach' : 'Tú' }}</strong>
              <p>{{ message.content }}</p>
            </li>
          }
        </ol>
        @if (session.loading()) { <p role="status">Analizando la situación...</p> }
        @if (session.fallbackModel(); as model) { <p role="status">Respondido por el modelo de respaldo: {{ model }}</p> }
        @if (session.error(); as error) {
          <div role="alert">
            <p>{{ error }}</p>
            @if (session.canRetry()) { <button type="button" class="btn-secondary" (click)="session.retry()">Reintentar</button> }
          </div>
        }
      </app-bento-card>

      <app-bento-card span="full" title="Tu pregunta">
        <form (ngSubmit)="submit()">
          <label for="chat-input">Escribe tu pregunta al coach</label>
          <textarea id="chat-input" name="message" [(ngModel)]="draft" maxlength="4000" rows="4" [disabled]="session.loading()"></textarea>
          <div class="actions">
            <span>{{ draft.length }}/4000 caracteres</span>
            <button type="submit" class="btn-primary" [disabled]="session.loading() || !draft.trim() || !auth.hasToken()">Enviar</button>
          </div>
        </form>
        @if (!auth.hasToken()) { <a routerLink="/cuenta">Inicia sesión para hablar con el coach.</a> }
      </app-bento-card>
    </section>
  `,
  styles: [`
    .chat-page { display: grid; gap: 20px; max-width: 1000px; margin: 0 auto; }
    .heading, .actions { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
    h1 { font-family: var(--font-family-display); margin: 0; }
    .context { color: var(--color-text-secondary); }
    .starters { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
    .starter, .btn-secondary { padding: 10px 14px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-card); color: var(--color-text-primary); cursor: pointer; }
    .messages { list-style: none; padding: 0; display: grid; gap: 12px; }
    .messages li { padding: 14px; border-radius: 10px; background: var(--color-bg-card); white-space: pre-wrap; overflow-wrap: anywhere; }
    .messages li.assistant { border-left: 3px solid var(--color-action-primary); }
    .messages p { margin-bottom: 0; }
    textarea { width: 100%; display: block; margin: 8px 0; padding: 12px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-bg-page); color: var(--color-text-primary); font: inherit; }
    .actions { flex-wrap: wrap; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatComponent {
  readonly session = inject(ChatSessionService);
  readonly active = inject(ActivePlayerService);
  readonly auth = inject(TokenService);
  readonly starters = [
    '¿Cómo mejoro mis intercambios?',
    '¿Cuándo debo ahorrar créditos?',
    '¿Cómo puedo posicionarme mejor?',
    '¿Qué debería practicar esta semana?',
  ];
  draft = '';

  constructor() {
    effect(() => {
      this.auth.currentToken();
      this.active.version();
      this.draft = '';
    });
  }

  ask(prompt: string): void {
    this.session.send(prompt);
  }

  submit(): void {
    if (this.session.send(this.draft)) this.draft = '';
  }

  reset(): void {
    this.draft = '';
    this.session.reset();
  }
}
