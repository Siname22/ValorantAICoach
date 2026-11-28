import { effect, inject, Injectable, signal } from '@angular/core';
import { ApiClientService } from '../../core/api/api-client.service';
import { ChatMessage, ChatRequest } from '../../core/api/api-models';
import { TokenService } from '../../core/auth/token.service';
import { ActivePlayerService } from '../../core/player/active-player.service';

@Injectable({ providedIn: 'root' })
export class ChatSessionService {
  private readonly api = inject(ApiClientService);
  private readonly token = inject(TokenService);
  private readonly active = inject(ActivePlayerService);
  private scope = '';
  private requestVersion = 0;
  private readonly failedPrompt = signal<string | null>(null);

  readonly messages = signal<ChatMessage[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly fallbackModel = signal<string | null>(null);
  readonly canRetry = this.failedPrompt.asReadonly();

  constructor() {
    effect(() => this.ensureScope());
  }

  private scopeKey(): string {
    const player = this.active.player();
    return JSON.stringify([
      this.token.currentToken(), this.active.version(),
      player?.gameName, player?.tagLine, player?.region,
    ]);
  }

  private ensureScope(): void {
    const next = this.scopeKey();
    if (next !== this.scope) {
      this.scope = next;
      this.reset();
    }
  }

  reset(): void {
    ++this.requestVersion;
    this.messages.set([]);
    this.loading.set(false);
    this.error.set(null);
    this.fallbackModel.set(null);
    this.failedPrompt.set(null);
  }

  send(raw: string): boolean {
    this.ensureScope();
    const message = raw.trim();
    if (!this.token.hasToken() || this.token.isExpired()) return false;
    if (!message || message.length > 4000 || this.loading()) {
      if (message.length > 4000) this.error.set('Máximo 4000 caracteres por mensaje.');
      return false;
    }
    const player = this.active.player();
    const history = this.messages().slice(-40);
    const request: ChatRequest = {
      message,
      history,
      player: player ? {
        game_name: player.gameName,
        tag_line: player.tagLine,
        region: player.region,
      } : null,
    };
    const version = ++this.requestVersion;
    const scope = this.scope;
    this.messages.set([...history, { role: 'user', content: message }]);
    this.loading.set(true);
    this.error.set(null);
    this.failedPrompt.set(null);
    this.api.chat(request).subscribe({
      next: response => {
        if (version !== this.requestVersion || this.scopeKey() !== scope) return;
        this.messages.set([
          ...this.messages(), { role: 'assistant', content: response.reply } as ChatMessage,
        ].slice(-40));
        this.fallbackModel.set(response.fallback_used ? response.model : null);
        this.loading.set(false);
      },
      error: (failure: { status?: number }) => {
        if (version !== this.requestVersion || this.scopeKey() !== scope) return;
        this.messages.set(this.messages().slice(0, -1));
        this.loading.set(false);
        this.failedPrompt.set(message);
        this.error.set(failure.status === 503
          ? 'El servicio de IA no está disponible ahora. Puedes reintentar.'
          : failure.status === 401 || failure.status === 403
            ? 'La sesión ha terminado. Inicia sesión de nuevo.'
            : 'El coach tuvo un problema. Puedes reintentar.');
      },
    });
    return true;
  }

  retry(): boolean {
    const prompt = this.failedPrompt();
    return prompt ? this.send(prompt) : false;
  }
}
