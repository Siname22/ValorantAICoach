import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { SummaryComponent } from './summary.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { of } from 'rxjs';

describe('SummaryComponent', () => {
  let component: SummaryComponent;
  let fixture: ComponentFixture<SummaryComponent>;
  let apiSpy: jasmine.SpyObj<ApiClientService>;

  beforeEach(async () => {
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
    expect(rowHeaders.length).toBeGreaterThan(0);
  });

  it('should not indicate victory or defeat using color alone', () => {
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
        matches_played: 10,
        win_rate: 0.6,
        kd_ratio: 1.4,
        avg_score: 250,
        headshot_pct: 0.25,
      })
    );
    apiSpy.getCoachingReports.and.returnValue(of({ reports: [], count: 0 }));

    component.onSearch();

    expect(apiSpy.getPlayer).toHaveBeenCalledWith('TestPlayer', 'EUW', 'eu');
  });

  it('should calculate ACS accurately from scored matches and not fabricate 231 or kd*180', () => {
    // When no matches or stats, calculatedAcs should be null
    component.matches.set([]);
    component.stats.set(null);
    expect(component.calculatedAcs()).toBeNull();

    // When matches have scores, average them
    component.matches.set([
      {
        match_id: 'm1',
        map_name: 'Ascent',
        result: 'Victory',
        kills: 20,
        deaths: 10,
        assists: 5,
        score: 300,
        agent_name: 'Jett',
      },
      {
        match_id: 'm2',
        map_name: 'Bind',
        result: 'Defeat',
        kills: 15,
        deaths: 15,
        assists: 2,
        score: 200,
        agent_name: 'Raze',
      },
    ]);
    expect(component.calculatedAcs()).toBe(250);

    // When no scored matches but stats has avg_score
    component.matches.set([]);
    component.stats.set({
      game_name: 'Test',
      tag_line: 'EUW',
      kills: 10,
      deaths: 10,
      assists: 5,
      kd_ratio: 1.0,
      win_pct: 0.5,
      headshot_pct: 0.2,
      avg_score: 275,
    } as any);
    expect(component.calculatedAcs()).toBe(275);

    // Total match score of 6000 without round count must NOT return 6000
    component.stats.set(null);
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

    // Ensure damage_per_round is never multiplied by 1.45 to invent ACS
    component.matches.set([]);
    component.stats.set({
      game_name: 'Test',
      tag_line: 'EUW',
      kills: 10,
      deaths: 10,
      assists: 5,
      kd_ratio: 1.0,
      win_pct: 0.5,
      headshot_pct: 0.2,
      damage_per_round: 150,
    } as any);
    expect(component.calculatedAcs()).toBeNull();
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
        score: 265,
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

