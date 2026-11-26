import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';
import { MatchesComponent } from './matches.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { ActivePlayerService } from '../../core/player/active-player.service';
import { MatchTimelineResponse, PlayerMatch } from '../../core/api/api-models';

const MATCH = {
  match_id: 'm-1',
  map_name: 'Ascent',
  agent_name: 'Jett',
  result: 'Victory',
  score: 284,
  kills: 22,
  deaths: 11,
  assists: 4,
  round_score: '13-9',
} satisfies PlayerMatch;
const LOSS = { ...MATCH, match_id: 'm-2', result: 'Defeat', map_name: 'Haven' };

describe('MatchesComponent', () => {
  let apiSpy: jasmine.SpyObj<ApiClientService>;
  let active: ActivePlayerService;

  function create(withPlayer = true) {
    const fixture = TestBed.createComponent(MatchesComponent);
    if (withPlayer) {
      active.set({ gameName: 'Alpha', tagLine: 'EU1', region: 'eu' });
    }
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(async () => {
    sessionStorage.clear();
    apiSpy = jasmine.createSpyObj('ApiClientService', ['getPlayerMatches', 'getMatchTimeline']);
    apiSpy.getPlayerMatches.and.returnValue(of({ matches: [MATCH, LOSS], count: 2 }));

    await TestBed.configureTestingModule({
      imports: [MatchesComponent],
      providers: [provideRouter([]), { provide: ApiClientService, useValue: apiSpy }],
    }).compileComponents();
    active = TestBed.inject(ActivePlayerService);
  });

  afterEach(() => sessionStorage.clear());

  it('loads matches for the selected player and region', () => {
    const f = create();
    expect(apiSpy.getPlayerMatches).toHaveBeenCalledWith('Alpha', 'EU1', 20, 'eu');
    expect(f.nativeElement.querySelectorAll('tbody tr').length).toBe(2);
    expect(f.nativeElement.textContent).toContain('Alpha#EU1');
  });

  it('renders an accessible table with caption and scoped headers', () => {
    const f = create();
    const table: HTMLTableElement = f.nativeElement.querySelector('table');
    expect(table.querySelector('caption')).toBeTruthy();
    expect(table.querySelectorAll('th[scope="col"]').length).toBe(7);
  });

  it('filters matches by result', () => {
    const f = create();
    f.componentInstance.filterResult = 'Victory';
    f.componentInstance.applyFilter();
    expect(f.componentInstance.filteredMatches().length).toBe(1);
  });

  it('asks the user to pick a player and does not call the API when none is selected', () => {
    const f = create(false);
    expect(apiSpy.getPlayerMatches).not.toHaveBeenCalled();
    expect(f.nativeElement.querySelector('[data-testid="no-player"]')).toBeTruthy();
    expect(f.nativeElement.querySelector('table')).toBeNull();
  });

  it('shows an error and NO fabricated matches when the API fails', () => {
    apiSpy.getPlayerMatches.and.returnValue(throwError(() => new Error('boom')));
    const f = create();
    expect(f.componentInstance.allMatches()).toEqual([]);
    expect(f.nativeElement.querySelector('[data-testid="load-error"]')).toBeTruthy();
    const text = f.nativeElement.textContent;
    expect(text).not.toContain('Ascent');
    expect(text).not.toContain('Haven');
    expect(text).not.toContain('Jett');
    expect(f.nativeElement.querySelectorAll('tbody tr').length).toBe(0);
  });

  it('shows an explicit empty state when the player has no matches', () => {
    apiSpy.getPlayerMatches.and.returnValue(of({ matches: [], count: 0 }));
    const f = create();
    expect(f.nativeElement.textContent).toContain('No hay partidas registradas');
  });

  it('ignores a late match response from the previously selected region', () => {
    const old = new Subject<{ matches: PlayerMatch[]; count: number }>();
    apiSpy.getPlayerMatches.and.returnValues(old, of({ matches: [LOSS], count: 1 }));
    const f = create();
    active.set({ gameName: 'Alpha', tagLine: 'EU1', region: 'na' });
    f.componentInstance.loadMatches();
    old.next({ matches: [MATCH], count: 1 });
    expect(f.componentInstance.allMatches().map((m) => m.match_id)).toEqual(['m-2']);
    expect(apiSpy.getPlayerMatches).toHaveBeenCalledWith('Alpha', 'EU1', 20, 'na');
  });

  it('shows rounds from the API timeline', () => {
    apiSpy.getMatchTimeline.and.returnValue(
      of({
        match_id: 'm-1',
        total_rounds: 1,
        rounds: [
          {
            round_num: 1,
            round_number: 1,
            winning_team: 'Team A',
            winning_side: 'attack',
            win_type: 'Eliminated',
            result: 'Won',
            loadout_value: 800,
            spent_credits: 700,
          },
        ],
      } as MatchTimelineResponse)
    );
    const f = create();
    f.componentInstance.inspectTimeline('m-1');
    f.detectChanges();
    expect(f.componentInstance.selectedTimeline()?.rounds?.length).toBe(1);
    expect(f.componentInstance.selectedMatchId()).toBe('m-1');
  });

  it('shows an error and NO demo rounds when the timeline request fails', () => {
    apiSpy.getMatchTimeline.and.returnValue(throwError(() => new Error('500')));
    const f = create();
    f.componentInstance.inspectTimeline('m-1');
    f.detectChanges();
    expect(f.componentInstance.selectedTimeline()).toBeNull();
    expect(f.nativeElement.querySelector('[data-testid="timeline-error"]')).toBeTruthy();
    expect(f.nativeElement.textContent).not.toContain('Ronda 1');
    expect(f.nativeElement.textContent).not.toContain('creds');
  });

  it('reports an empty timeline instead of inventing rounds', () => {
    apiSpy.getMatchTimeline.and.returnValue(
      of({ match_id: 'm-1', total_rounds: 0, rounds: [] } satisfies MatchTimelineResponse)
    );
    const f = create();
    f.componentInstance.inspectTimeline('m-1');
    f.detectChanges();
    expect(f.componentInstance.selectedTimeline()).toBeNull();
    expect(f.nativeElement.querySelector('[data-testid="timeline-error"]')).toBeTruthy();
  });
});
