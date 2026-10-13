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
});
