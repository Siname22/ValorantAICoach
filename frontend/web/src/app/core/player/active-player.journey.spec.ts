import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ApiClientService } from '../api/api-client.service';
import { PlayerMatch, PlayerStatsOverview } from '../api/api-models';
import { ActivePlayerService } from './active-player.service';
import { SummaryComponent } from '../../features/summary/summary.component';
import { MatchesComponent } from '../../features/matches/matches.component';
import { ReportsComponent } from '../../features/reports/reports.component';
import { routes } from '../../app.routes';
import { authGuard } from '../auth/auth.guard';

/**
 * Journey: the player chosen on the summary screen is the one used by the matches
 * and reports screens, and changing it changes the data in all three.
 */
describe('Active player journey (summary -> matches -> reports)', () => {
  let api: jasmine.SpyObj<ApiClientService>;

  const profile = (name: string, tag: string, region: string) =>
    ({ game_name: name, tag_line: tag, region });

  beforeEach(async () => {
    sessionStorage.clear();
    api = jasmine.createSpyObj('ApiClientService', [
      'getPlayer',
      'getPlayerMatches',
      'getPlayerStats',
      'getCoachingReports',
      'getPlayerProgression',
    ]);
    api.getPlayer.and.callFake((n: string, t: string, r?: string) => of(profile(n, t, r || '')));
    api.getPlayerStats.and.returnValue(of({
      kills: 0, deaths: 0, assists: 0, kd_ratio: 0, win_pct: 0, headshot_pct: 0,
    } satisfies PlayerStatsOverview));
    api.getPlayerProgression.and.returnValue(throwError(() => new Error('unavailable')));
    api.getPlayerMatches.and.callFake((n: string) =>
      of({
        matches: [{ match_id: 'm-' + n, map_name: 'Map-' + n, agent_name: 'Agent-' + n, result: 'Victory', kills: 1, deaths: 0, assists: 0 } satisfies PlayerMatch],
        count: 1,
      })
    );
    api.getCoachingReports.and.callFake((n: string) =>
      of({ reports: [{ id: 'r-' + n, summary: 'Informe de ' + n, created_at: '2026-11-20T10:00:00Z' }], count: 1 })
    );

    await TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: ApiClientService, useValue: api }],
    }).compileComponents();
  });

  afterEach(() => sessionStorage.clear());

  function search(riotId: string, region: string) {
    const f = TestBed.createComponent(SummaryComponent);
    f.detectChanges();
    f.componentInstance.searchQuery = riotId;
    f.componentInstance.selectedRegion = region;
    f.componentInstance.onSearch();
    f.detectChanges();
    return f;
  }

  function matchesText(): string {
    const f = TestBed.createComponent(MatchesComponent);
    f.detectChanges();
    return f.nativeElement.textContent;
  }

  function reportsText(): string {
    const f = TestBed.createComponent(ReportsComponent);
    f.detectChanges();
    return f.nativeElement.textContent;
  }

  it('propagates the selected identity and region to matches and reports', () => {
    search('Alpha#EU1', 'eu');

    expect(TestBed.inject(ActivePlayerService).player()).toEqual({
      gameName: 'Alpha', tagLine: 'EU1', region: 'eu',
    });
    expect(matchesText()).toContain('Alpha#EU1');
    expect(api.getPlayerMatches).toHaveBeenCalledWith('Alpha', 'EU1', 20, 'eu');
    const rt = reportsText();
    expect(rt).toContain('Alpha#EU1');
    expect(rt).toContain('Informe de Alpha');
    expect(api.getCoachingReports).toHaveBeenCalledWith('Alpha', 'EU1', 20, 'eu');
  });

  it('switching player replaces the data in every screen (no leftovers from the previous one)', () => {
    search('Alpha#EU1', 'eu');
    search('Beta#NA2', 'na');

    const mt = matchesText();
    expect(mt).toContain('Beta#NA2');
    expect(mt).toContain('Map-Beta');
    expect(mt).not.toContain('Alpha');
    expect(api.getPlayerMatches).toHaveBeenCalledWith('Beta', 'NA2', 20, 'na');

    const rt = reportsText();
    expect(rt).toContain('Informe de Beta');
    expect(rt).not.toContain('Alpha');
    expect(api.getCoachingReports).toHaveBeenCalledWith('Beta', 'NA2', 20, 'na');
  });

  it('summary restores the same identity when the user navigates back to it', () => {
    search('Alpha#EU1', 'latam');
    api.getPlayer.calls.reset();

    const f = TestBed.createComponent(SummaryComponent);
    f.detectChanges();
    expect(f.componentInstance.searchQuery).toBe('Alpha#EU1');
    expect(f.componentInstance.selectedRegion).toBe('latam');
    expect(api.getPlayer).toHaveBeenCalledWith('Alpha', 'EU1', 'latam');
  });

  it('restores the active identity from session storage after a reload', () => {
    search('Alpha#EU1', 'latam');
    expect(new ActivePlayerService().player()).toEqual({
      gameName: 'Alpha', tagLine: 'EU1', region: 'latam',
    });
  });

  it('keeps public search and matches routes while guarding reports', () => {
    expect(routes.find((route) => route.path === 'resumen')?.canActivate).toBeUndefined();
    expect(routes.find((route) => route.path === 'partidas')?.canActivate).toBeUndefined();
    expect(routes.find((route) => route.path === 'informes')?.canActivate).toContain(authGuard);
  });

  it('API failures never produce demo data on any screen', () => {
    search('Alpha#EU1', 'eu');
    api.getPlayerMatches.and.returnValue(throwError(() => new Error('500')));
    api.getCoachingReports.and.returnValue(throwError(() => new Error('500')));

    const mt = matchesText();
    const rt = reportsText();
    for (const text of [mt, rt]) {
      expect(text).not.toContain('TenZ');
      expect(text).not.toContain('Ascent');
      expect(text).not.toContain('Jett');
      expect(text).not.toContain('report-demo');
    }
    expect(mt).toContain('No se pudieron cargar las partidas');
    expect(rt).toContain('No se pudo cargar el historial');
  });

  it('summary shows no demo plan or demo player when the report API fails', () => {
    api.getCoachingReports.and.returnValue(throwError(() => new Error('500')));
    const f = search('Alpha#EU1', 'eu');
    const text = f.nativeElement.textContent;
    expect(text).not.toContain('Disciplina en Ronda 3');
    expect(text).not.toContain('B Main');
    expect(f.componentInstance.latestPlanItems()).toEqual([]);
  });
});
