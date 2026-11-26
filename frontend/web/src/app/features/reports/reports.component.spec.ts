import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { ReportsComponent } from './reports.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import { CoachingReportDetailResponse, CoachingReportSummary } from '../../core/api/api-models';

describe('ReportsComponent', () => {
  let apiSpy: jasmine.SpyObj<ApiClientService>;
  let active: ActivePlayerService;

  function create(withPlayer = true) {
    if (withPlayer) {
      active.set({ gameName: 'Alpha', tagLine: 'EU1', region: 'eu' });
    }
    const fixture = TestBed.createComponent(ReportsComponent);
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(async () => {
    sessionStorage.clear();
    apiSpy = jasmine.createSpyObj('ApiClientService', [
      'getCoachingReports',
      'getPlayerProgression',
      'generateCoachingReport',
    ]);
    apiSpy.getCoachingReports.and.returnValue(of({ reports: [], count: 0 }));
    apiSpy.getPlayerProgression.and.returnValue(throwError(() => new Error('unavailable')));

    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [provideRouter([]), { provide: ApiClientService, useValue: apiSpy }],
    }).compileComponents();
    active = TestBed.inject(ActivePlayerService);
  });

  afterEach(() => sessionStorage.clear());

  it('never renders the demo identity, demo report or fixed figures', () => {
    const f = create();
    const text = f.nativeElement.textContent;
    expect(text).not.toContain('TenZ');
    expect(text).not.toContain('report-demo');
    expect(text).not.toContain('Optimización de disciplina económica');
    expect(text).not.toContain('74%');
    expect(text).not.toContain('89%');
    expect(text).not.toContain('A-');
    expect(text).not.toContain('+12.4');
  });

  it('keeps the four agent descriptions', () => {
    const text = create().nativeElement.textContent;
    for (const n of ['Match Analyst', 'Economy Coach', 'Role Coach', 'Report Writer']) {
      expect(text).toContain(n);
    }
  });

  it('loads the report history from the API for the selected player and region', () => {
    apiSpy.getCoachingReports.and.returnValue(
      of({
        reports: [
          {
            id: 'r-1',
            created_at: '2026-11-20T10:00:00Z',
            payload: {
              executive_summary: 'Resumen real',
              key_strengths: ['Buen uso de utilidad'],
              critical_flaws: ['Economía irregular'],
            },
          },
          { id: 'r-2', created_at: '2026-11-19T10:00:00Z', summary: 'Otro', strengths: '', weaknesses: '' },
        ],
        count: 2,
      })
    );
    const f = create();
    expect(apiSpy.getCoachingReports).toHaveBeenCalledWith('Alpha', 'EU1', 20, 'eu');
    expect(apiSpy.getPlayerProgression).toHaveBeenCalledWith('Alpha', 'EU1', 'eu');
    expect(f.componentInstance.reports().map((r) => r.id)).toEqual(['r-1', 'r-2']);
    const text = f.nativeElement.textContent;
    expect(text).toContain('Resumen real');
    expect(text).toContain('Economía irregular');
    expect(text).toContain('Alpha#EU1');
  });

  it('shows an explicit empty state when the player has no reports', () => {
    const f = create();
    expect(f.nativeElement.querySelector('[data-testid="empty-history"]')).toBeTruthy();
    expect(f.componentInstance.reports().length).toBe(0);
  });

  it('shows a loading state while the history is pending', () => {
    const pending = new Subject<{ reports: CoachingReportSummary[]; count: number }>();
    apiSpy.getCoachingReports.and.returnValue(pending);
    const f = create();
    expect(f.nativeElement.querySelector('[data-testid="loading"]')).toBeTruthy();
  });

  it('ignores late history from an earlier selection of the same identity', () => {
    const old = new Subject<{ reports: CoachingReportSummary[]; count: number }>();
    apiSpy.getCoachingReports.and.returnValues(
      old,
      of({ reports: [{ id: 'current', summary: 'Actual' }], count: 1 })
    );
    const f = create();
    active.set({ gameName: 'Alpha', tagLine: 'EU1', region: 'na' });
    f.componentInstance.loadHistory();
    old.next({ reports: [{ id: 'old', summary: 'Anterior' }], count: 1 });
    expect(f.componentInstance.reports().map((report) => report.id)).toEqual(['current']);
  });

  it('shows an error and no fabricated reports when the history request fails', () => {
    apiSpy.getCoachingReports.and.returnValue(throwError(() => new Error('503')));
    const f = create();
    expect(f.nativeElement.querySelector('[data-testid="history-error"]')).toBeTruthy();
    expect(f.componentInstance.reports()).toEqual([]);
    expect(f.nativeElement.querySelector('.report-item')).toBeNull();
    expect(f.nativeElement.textContent).not.toContain('TenZ');
  });

  it('asks to select a player and does not call the API when none is selected', () => {
    const f = create(false);
    expect(apiSpy.getCoachingReports).not.toHaveBeenCalled();
    expect(f.nativeElement.querySelector('[data-testid="no-player"]')).toBeTruthy();
    expect(f.nativeElement.querySelector('button.btn-primary').disabled).toBeTrue();
  });

  it('generates a report for the active player and region and prepends it', () => {
    apiSpy.generateCoachingReport.and.returnValue(
      of({
        id: 'new-1',
        payload: { executive_summary: 'Nuevo', key_strengths: ['A'], critical_flaws: ['B'] },
        created_at: '2026-11-25T10:00:00Z',
      } satisfies CoachingReportDetailResponse)
    );
    const f = create();
    f.componentInstance.onGenerateReport();
    expect(apiSpy.generateCoachingReport).toHaveBeenCalledWith('Alpha', 'EU1', 5, 'eu');
    expect(f.componentInstance.reports()[0].id).toBe('new-1');
    expect(f.componentInstance.statusMessage()).toContain('éxito');
  });

  it('does not claim success when the backend returns no report', () => {
    apiSpy.generateCoachingReport.and.returnValue(of({ status: 'insufficient_data' } as CoachingReportDetailResponse));
    const f = create();
    f.componentInstance.onGenerateReport();
    expect(f.componentInstance.reports().length).toBe(0);
    expect(f.componentInstance.statusMessage()).not.toContain('éxito');
  });

  it('surfaces the API error when generation fails', () => {
    apiSpy.generateCoachingReport.and.returnValue(
      throwError(() => ({ error: { detail: 'Sin partidas suficientes' } }))
    );
    const f = create();
    f.componentInstance.onGenerateReport();
    expect(f.componentInstance.statusMessage()).toBe('Sin partidas suficientes');
    expect(f.componentInstance.reports().length).toBe(0);
  });
});
