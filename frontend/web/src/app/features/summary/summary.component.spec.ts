import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { SummaryComponent } from './summary.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { of, Subject } from 'rxjs';
import { PlayerProfile } from '../../core/api/api-models';

describe('SummaryComponent', () => {
  let component: SummaryComponent;
  let fixture: ComponentFixture<SummaryComponent>;
  let apiSpy: jasmine.SpyObj<ApiClientService>;

  beforeEach(async () => {
    sessionStorage.clear();
    apiSpy = jasmine.createSpyObj('ApiClientService', [
      'getPlayer',
      'getPlayerMatches',
      'getPlayerStats',
      'getCoachingReports',
      'syncPlayer',
    ]);

    await TestBed.configureTestingModule({
      imports: [SummaryComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiClientService, useValue: apiSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the summary bento grid component', () => {
    expect(component).toBeTruthy();
  });

  it('shows no example matches, ACS comparison, or drawn economy trend before a search', () => {
    const text: string = fixture.nativeElement.textContent;
    expect(text).not.toContain('Ascent');
    expect(text).not.toContain('22 / 11 / 4');
    expect(text).not.toContain('por encima de la media de tu rango');
    expect(fixture.nativeElement.querySelector('.economy-chart-svg')).toBeNull();
  });

  it('should render hero search form with role="search" and associated label', () => {
    const searchForm: HTMLElement = fixture.nativeElement.querySelector('form[role="search"]');
    expect(searchForm).toBeTruthy();

    const label: HTMLLabelElement = fixture.nativeElement.querySelector('label[for="riot-id-search"]');
    expect(label).toBeTruthy();

    const input: HTMLInputElement = fixture.nativeElement.querySelector('#riot-id-search');
    expect(input).toBeTruthy();
  });

  it('should render matches table with accessible caption and scoped headers', () => {
    const table: HTMLTableElement = fixture.nativeElement.querySelector('table');
    expect(table).toBeTruthy();

    const caption = table.querySelector('caption');
    expect(caption).toBeTruthy();

    const colHeaders = table.querySelectorAll('th[scope="col"]');
    expect(colHeaders.length).toBe(6);

    const rowHeaders = table.querySelectorAll('th[scope="row"]');
    expect(rowHeaders.length).toBe(0);
    expect(table.textContent).toContain('Busca un jugador');
  });

  it('should not indicate victory or defeat using color alone', () => {
    component.matches.set([
      { match_id: 'm-win', map_name: 'Ascent', agent_name: 'Jett', result: 'Victory', kills: 1, deaths: 0, assists: 1 },
      { match_id: 'm-loss', map_name: 'Bind', agent_name: 'Sova', result: 'Defeat', kills: 0, deaths: 1, assists: 0 },
    ]);
    fixture.detectChanges();
    const victorySpan: HTMLElement = fixture.nativeElement.querySelector('.text-victory');
    expect(victorySpan).toBeTruthy();
    expect(victorySpan.textContent).toContain('▲');

    const defeatSpan: HTMLElement = fixture.nativeElement.querySelector('.text-defeat');
    expect(defeatSpan).toBeTruthy();
    expect(defeatSpan.textContent).toContain('▼');
  });

  it('should switch economy chart view between trend and round-by-round', () => {
    expect(component.economyMode()).toBe('trend');

    const roundsTab: HTMLButtonElement = fixture.nativeElement.querySelector('#tab-econ-rounds');
    roundsTab.click();
    fixture.detectChanges();

    expect(component.economyMode()).toBe('rounds');
    const desc = fixture.nativeElement.querySelector('#econ-rounds-desc');
    expect(desc).toBeTruthy();
  });

  it('should call API on valid search query', () => {
    component.searchQuery = 'TestPlayer#EUW';
    apiSpy.getPlayer.and.returnValue(
      of({
        game_name: 'TestPlayer',
        tag_line: 'EUW',
        region: 'eu',
        puuid: 'puuid-1',
        created_at: '2026-01-01',
      })
    );
    apiSpy.getPlayerMatches.and.returnValue(of({ matches: [], count: 0 }));
    apiSpy.getPlayerStats.and.returnValue(
      of({
        game_name: 'TestPlayer',
        tag_line: 'EUW',
        region: 'eu',
        kills: 20,
        deaths: 10,
        assists: 5,
        matches_played: 10,
        win_rate: 0.6,
        win_pct: 0.6,
        kd_ratio: 1.4,
        avg_score: 250,
        headshot_pct: 0.25,
      })
    );
    apiSpy.getCoachingReports.and.returnValue(of({ reports: [], count: 0 }));

    const regionSelect: HTMLSelectElement = fixture.nativeElement.querySelector('#region-select');
    regionSelect.value = 'na';
    regionSelect.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    component.onSearch();

    expect(component.selectedRegion).toBe('na');
    expect(apiSpy.getPlayer).toHaveBeenCalledWith('TestPlayer', 'EUW', 'na');
  });

  it('ignores an old search response after switching player, region, and back', () => {
    const first = new Subject<PlayerProfile>();
    const second = new Subject<PlayerProfile>();
    const third = new Subject<PlayerProfile>();
    apiSpy.getPlayer.and.returnValues(first, second, third);
    apiSpy.getPlayerMatches.and.returnValue(of({ matches: [], count: 0 }));
    apiSpy.getPlayerStats.and.returnValue(of({
      kills: 0, deaths: 0, assists: 0, kd_ratio: 0, win_pct: 0, headshot_pct: 0,
    }));
    apiSpy.getCoachingReports.and.returnValue(of({ reports: [], count: 0 }));

    component.searchQuery = 'Alpha#EU1';
    component.selectedRegion = 'eu';
    component.onSearch();
    fixture.detectChanges();
    const submitButton: HTMLButtonElement = fixture.nativeElement.querySelector('.hero-btn');
    expect(submitButton.disabled).toBeFalse();
    expect(submitButton.textContent).toContain('ACTUALIZAR BÚSQUEDA');
    component.searchQuery = 'Beta#NA1';
    component.selectedRegion = 'na';
    component.onSearch();
    component.searchQuery = 'Alpha#EU1';
    component.selectedRegion = 'eu';
    component.onSearch();

    first.next({ game_name: 'Alpha', tag_line: 'EU1', region: 'eu' });
    second.next({ game_name: 'Beta', tag_line: 'NA1', region: 'na' });
    expect(component.playerProfile()).toBeNull();
    expect(apiSpy.getPlayerMatches).not.toHaveBeenCalled();

    third.next({ game_name: 'Alpha', tag_line: 'EU1', region: 'eu' });
    expect(component.playerProfile()?.game_name).toBe('Alpha');
    expect(apiSpy.getPlayerMatches).toHaveBeenCalledTimes(1);
    expect(apiSpy.getPlayerMatches).toHaveBeenCalledWith('Alpha', 'EU1', 5, 'eu');
  });

  it('does not let an earlier match response replace post-sync matches', () => {
    const pending = new Subject<{ matches: import('../../core/api/api-models').PlayerMatch[]; count: number }>();
    const freshMatch = {
      match_id: 'fresh', map_name: 'Ascent', result: 'Victory',
      kills: 2, deaths: 1, assists: 1, agent_name: 'Sova',
    };
    const oldMatch = { ...freshMatch, match_id: 'old' };
    apiSpy.getPlayer.and.returnValue(of({ game_name: 'Alpha', tag_line: 'TEST', region: 'eu' }));
    apiSpy.getPlayerMatches.and.returnValues(pending, of({ matches: [freshMatch], count: 1 }));
    apiSpy.getCoachingReports.and.returnValue(of({ reports: [], count: 0 }));
    apiSpy.syncPlayer.and.returnValue(of({ status: 'ok', new_report_generated: false }));
    component.searchQuery = 'Alpha#TEST';
    component.selectedRegion = 'eu';
    component.onSearch();
    component.onSync();
    pending.next({ matches: [oldMatch], count: 1 });
    expect(component.matches().map((match) => match.match_id)).toEqual(['fresh']);
  });

  it('should calculate ACS accurately from scored matches and not fabricate 231 or kd*180', () => {
    // When no matches, calculatedAcs should be null.
    component.matches.set([]);
    expect(component.calculatedAcs()).toBeNull();

    // When matches have total scores and round_score, divide total score by rounds
    component.matches.set([
      {
        match_id: 'm1',
        map_name: 'Ascent',
        result: 'Victory',
        kills: 20,
        deaths: 10,
        assists: 5,
        score: 6000,
        round_score: '13 - 7', // 20 rounds -> ACS 300
        agent_name: 'Jett',
      },
      {
        match_id: 'm2',
        map_name: 'Bind',
        result: 'Defeat',
        kills: 15,
        deaths: 15,
        assists: 2,
        score: 4000,
        round_score: '7 - 13', // 20 rounds -> ACS 200
        agent_name: 'Raze',
      },
    ]);
    expect(component.calculatedAcs()).toBe(250);

    // Total score of 400 with 24 rounds ('13 - 11') calculates 17 ACS (never 400)
    component.matches.set([
      {
        match_id: 'm-low-score',
        map_name: 'Ascent',
        result: 'Defeat',
        kills: 2,
        deaths: 18,
        assists: 1,
        score: 400,
        round_score: '13 - 11',
        agent_name: 'Cypher',
      },
    ]);
    expect(component.calculatedAcs()).toBe(17);

    // Total score of 400 WITHOUT round count must NOT be assumed to be 400 ACS
    component.matches.set([
      {
        match_id: 'm-no-rounds-low',
        map_name: 'Ascent',
        result: 'Defeat',
        kills: 2,
        deaths: 18,
        assists: 1,
        score: 400,
        agent_name: 'Cypher',
      },
    ]);
    expect(component.calculatedAcs()).toBeNull();

    // Vision provider matches provide direct ACS via provider_score
    component.matches.set([
      {
        match_id: 'm-vision',
        map_name: 'Split',
        result: 'Victory',
        kills: 22,
        deaths: 12,
        assists: 4,
        score: null,
        provider_score: 285,
        provider: 'vision',
        round_score: '13 - 9',
        agent_name: 'Reyna',
      },
    ]);
    expect(component.calculatedAcs()).toBe(285);

    // Two matches with ACS 0 and 250 must average to 125 (never discarding 0 score)
    component.matches.set([
      {
        match_id: 'm-zero',
        map_name: 'Ascent',
        result: 'Defeat',
        kills: 0,
        deaths: 15,
        assists: 0,
        score: 0,
        round_score: '13 - 11', // 24 rounds -> ACS 0
        agent_name: 'Sova',
      },
      {
        match_id: 'm-250',
        map_name: 'Bind',
        result: 'Victory',
        kills: 20,
        deaths: 10,
        assists: 5,
        score: 6000,
        round_score: '13 - 11', // 24 rounds -> ACS 250
        agent_name: 'Jett',
      },
    ]);
    expect(component.calculatedAcs()).toBe(125);

    // Total match score of 6000 without round count must NOT return 6000
    component.matches.set([
      {
        match_id: 'm-high',
        map_name: 'Haven',
        result: 'Victory',
        kills: 25,
        deaths: 12,
        assists: 5,
        score: 6000,
        agent_name: 'Jett',
      },
    ]);
    expect(component.calculatedAcs()).toBeNull();

    // Total match score of 6000 WITH round_score '13 - 11' (24 rounds) divides correctly
    component.matches.set([
      {
        match_id: 'm-high-rounds',
        map_name: 'Haven',
        result: 'Victory',
        kills: 25,
        deaths: 12,
        assists: 5,
        score: 6000,
        round_score: '13 - 11',
        agent_name: 'Jett',
      },
    ]);
    expect(component.calculatedAcs()).toBe(250);

  });

  it('should render real match metrics and not display hardcoded 13 - 9 or fake 240', () => {
    component.matches.set([
      {
        match_id: 'm1',
        map_name: 'Split',
        result: 'Victory',
        kills: 18,
        deaths: 12,
        assists: 7,
        score: 5035,
        round_score: '13 - 6',
        agent_name: 'Omen',
      },
      {
        match_id: 'm2',
        map_name: 'Lotus',
        result: 'Defeat',
        kills: 10,
        deaths: 14,
        assists: 3,
        agent_name: 'Fade',
      },
    ]);
    fixture.detectChanges();

    const tableText = fixture.nativeElement.querySelector('table').textContent;
    // Real match 1
    expect(tableText).toContain('13 - 6');
    expect(tableText).toContain('265');
    // Real match 2 without score or round_score should render dash, not 13 - 9 or 240
    expect(tableText).not.toContain('13 - 9');
    expect(tableText).not.toContain('240');
  });

  it('should not display hardcoded 72.5% economy narrative', () => {
    fixture.detectChanges();
    const trendDesc = fixture.nativeElement.querySelector('#econ-trend-desc');
    expect(trendDesc.textContent).not.toContain('72.5%');
  });
});

