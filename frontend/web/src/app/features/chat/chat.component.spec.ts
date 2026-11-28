import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Subject } from 'rxjs';
import { ApiClientService } from '../../core/api/api-client.service';
import { ChatResponse } from '../../core/api/api-models';
import { TokenService } from '../../core/auth/token.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import { ChatComponent } from './chat.component';

describe('ChatComponent', () => {
  let api: jasmine.SpyObj<ApiClientService>;

  beforeEach(async () => {
    sessionStorage.clear();
    api = jasmine.createSpyObj('ApiClientService', ['chat']);
    await TestBed.configureTestingModule({
      imports: [ChatComponent],
      providers: [provideRouter([]), { provide: ApiClientService, useValue: api }],
    }).compileComponents();
    const token = TestBed.inject(TokenService);
    token.setToken(`x.${btoa(JSON.stringify({ sub: 'user-a', exp: 9999999999 }))}.x`);
    TestBed.inject(ActivePlayerService).set({ gameName: 'Alpha', tagLine: 'TAG', region: 'eu' });
  });

  afterEach(() => sessionStorage.clear());

  it('renders starters, loading, response and reset through the visible interface', () => {
    const response = new Subject<ChatResponse>();
    api.chat.and.returnValue(response);
    const fixture = TestBed.createComponent(ChatComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('.starter').length).toBe(4);
    const starter: HTMLButtonElement = fixture.nativeElement.querySelector('.starter');
    starter.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Analizando la situación');
    response.next({ reply: 'Practica los intercambios.', model: 'backup', fallback_used: true });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Practica los intercambios.');
    expect(fixture.nativeElement.textContent).toContain('modelo de respaldo');
    const reset: HTMLButtonElement = fixture.nativeElement.querySelector('.heading button');
    reset.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Practica los intercambios.');
  });

  it('can clear a failed first question and removes a draft when the player changes', () => {
    const response = new Subject<ChatResponse>();
    api.chat.and.returnValue(response);
    const fixture = TestBed.createComponent(ChatComponent);
    fixture.detectChanges();
    const starter: HTMLButtonElement = fixture.nativeElement.querySelector('.starter');
    starter.click();
    response.error({ status: 503 });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Puedes reintentar');
    const reset: HTMLButtonElement = fixture.nativeElement.querySelector('.heading button');
    expect(reset.disabled).toBeFalse();
    reset.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Puedes reintentar');

    fixture.componentInstance.draft = 'Pregunta privada';
    TestBed.inject(ActivePlayerService).set({ gameName: 'Beta', tagLine: 'TAG', region: 'na' });
    fixture.detectChanges();
    expect(fixture.componentInstance.draft).toBe('');
  });
});
