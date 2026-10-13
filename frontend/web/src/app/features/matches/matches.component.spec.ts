import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MatchesComponent } from './matches.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { of } from 'rxjs';

describe('MatchesComponent', () => {
  let component: MatchesComponent;
  let fixture: ComponentFixture<MatchesComponent>;
  let apiSpy: jasmine.SpyObj<ApiClientService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiClientService', ['getMatchTimeline']);

    await TestBed.configureTestingModule({
      imports: [MatchesComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiClientService, useValue: apiSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MatchesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the matches component', () => {
    expect(component).toBeTruthy();
  });

  it('should render accessible table with caption, col headers, and row headers', () => {
    const table: HTMLTableElement = fixture.nativeElement.querySelector('table');
    expect(table).toBeTruthy();

    const caption = table.querySelector('caption');
    expect(caption).toBeTruthy();

    const colHeaders = table.querySelectorAll('th[scope="col"]');
    expect(colHeaders.length).toBe(7);

    const rows = table.querySelectorAll('tbody tr');
    expect(rows.length).toBe(3);
  });

  it('should filter matches when select filter changes', () => {
    component.filterResult = 'Victory';
    component.applyFilter();
    fixture.detectChanges();

    expect(component.filteredMatches().length).toBe(2);

    component.filterResult = 'Defeat';
    component.applyFilter();
    fixture.detectChanges();

    expect(component.filteredMatches().length).toBe(1);
  });

  it('should inspect timeline when button is clicked', () => {
    apiSpy.getMatchTimeline.and.returnValue(
      of({
        match_id: 'match-101',
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
      })
    );

    component.inspectTimeline('match-101');
    fixture.detectChanges();

    expect(component.selectedTimeline()).toBeTruthy();
    expect(component.selectedMatchId()).toBe('match-101');
  });
});
