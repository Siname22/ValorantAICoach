import { TestBed } from '@angular/core/testing';
import { of, Subject } from 'rxjs';
import { ApiClientService } from '../../core/api/api-client.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import { TokenService } from '../../core/auth/token.service';
import { ChatResponse } from '../../core/api/api-models';
import { ChatSessionService } from './chat-session.service';

describe('ChatSessionService', () => {
  let api: jasmine.SpyObj<ApiClientService>;
  let active: ActivePlayerService;
  let token: TokenService;
  let chat: ChatSessionService;

  const jwt = (sub: string) => `x.${btoa(JSON.stringify({ sub, exp: 9999999999 }))}.x`;

  beforeEach(() => {
    sessionStorage.clear();
    api = jasmine.createSpyObj('ApiClientService', ['chat']);
    TestBed.configureTestingModule({ providers: [{ provide: ApiClientService, useValue: api }] });
    active = TestBed.inject(ActivePlayerService);
    token = TestBed.inject(TokenService);
    token.setToken(jwt('user-a'));
    active.set({ gameName: 'Alpha', tagLine: 'TAG', region: 'eu' });
    chat = TestBed.inject(ChatSessionService);
    TestBed.flushEffects();
  });

  afterEach(() => sessionStorage.clear());

  it('sends bounded history and selected region, then shows the reply', () => {
    const response = new Subject<ChatResponse>();
    api.chat.and.returnValue(response);
    expect(chat.send('¿Cómo mejoro?')).toBeTrue();
    expect(api.chat).toHaveBeenCalledWith({
      message: '¿Cómo mejoro?', history: [],
      player: { game_name: 'Alpha', tag_line: 'TAG', region: 'eu' },
    });
    response.next({ reply: 'Practica los intercambios.', model: 'backup', fallback_used: true });
    expect(chat.messages().map(m => m.role)).toEqual(['user', 'assistant']);
    expect(chat.fallbackModel()).toBe('backup');
  });

  it('discards late responses and history after switching player or logging out', () => {
    const first = new Subject<ChatResponse>();
    const second = new Subject<ChatResponse>();
    api.chat.and.returnValues(first, second);
    chat.send('Primera pregunta');
    active.set({ gameName: 'Beta', tagLine: 'TAG', region: 'na' });
    TestBed.flushEffects();
    first.next({ reply: 'Respuesta anterior', model: 'primary', fallback_used: false });
    expect(chat.messages()).toEqual([]);
    chat.send('Segunda pregunta');
    token.clearToken();
    TestBed.flushEffects();
    second.next({ reply: 'Respuesta privada', model: 'primary', fallback_used: false });
    expect(chat.messages()).toEqual([]);
  });

  it('rejects oversized input, exposes safe errors, and retries without keeping a failed turn', () => {
    expect(chat.send('x'.repeat(4001))).toBeFalse();
    expect(api.chat).not.toHaveBeenCalled();
    const failed = new Subject<ChatResponse>();
    const retried = new Subject<ChatResponse>();
    api.chat.and.returnValues(failed, retried);
    chat.send('Ayuda');
    failed.error({ status: 503, error: { detail: 'private upstream body' } });
    expect(chat.messages()).toEqual([]);
    expect(chat.error()).not.toContain('private upstream body');
    expect(chat.retry()).toBeTrue();
    retried.next({ reply: 'Inténtalo de nuevo.', model: 'primary', fallback_used: false });
    expect(chat.messages().length).toBe(2);
    chat.reset();
    expect(chat.messages()).toEqual([]);
  });

  it('keeps only the most recent 20 completed turns', () => {
    api.chat.and.returnValue(of({ reply: 'Respuesta', model: 'primary', fallback_used: false }));
    for (let i = 0; i < 22; i++) expect(chat.send(`Pregunta ${i}`)).toBeTrue();
    expect(chat.messages().length).toBe(40);
    expect(api.chat.calls.mostRecent().args[0].history.length).toBe(40);
    expect(chat.messages()[0].content).toBe('Pregunta 2');
  });
});
