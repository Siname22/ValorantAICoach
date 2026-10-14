import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ReportsComponent } from './reports.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { of } from 'rxjs';

describe('ReportsComponent', () => {
  let component: ReportsComponent;
  let fixture: ComponentFixture<ReportsComponent>;
  let apiSpy: jasmine.SpyObj<ApiClientService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiClientService', [
      'getPlayerProgression',
      'generateCoachingReport',
    ]);

    apiSpy.getPlayerProgression.and.returnValue(
      of({
        game_name: 'TenZ',
        tag_line: '0001',
        history_points: [],
        overall_trend: 'Positiva',
      })
    );

    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiClientService, useValue: apiSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ReportsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the reports component', () => {
    expect(component).toBeTruthy();
  });

  it('should render multi-agent overview cards (Match Analyst, Economy Coach, Role Coach, Report Writer)', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Match Analyst');
    expect(text).toContain('Economy Coach');
    expect(text).toContain('Role Coach');
    expect(text).toContain('Report Writer');
  });

  it('should trigger coaching report generation on button click', () => {
    apiSpy.generateCoachingReport.and.returnValue(
      of({
        status: 'completed',
        report: {
          id: 'new-report-1',
          player_id: 'p-1',
          payload: {},
          summary: 'Nuevo análisis táctico completado.',
          strengths: 'First bloods sólidos.',
          weaknesses: 'Compras desfasadas.',
          created_at: '2026-10-13T10:00:00Z',
        },
      })
    );

    component.onGenerateReport();

    expect(apiSpy.generateCoachingReport).toHaveBeenCalledWith('TenZ', '0001', 5);
    expect(component.reports().length).toBe(2);
    expect(component.statusMessage()).toContain('éxito');
  });

  it('should incorporate direct CoachingReportResponse returned by backend', () => {
    apiSpy.generateCoachingReport.and.returnValue(
      of({
        id: 'direct-report-101',
        player_id: 'p-1',
        schema_version: 1,
        provider: 'orchestrator',
        payload: {
          title: 'Direct Report Title',
          executive_summary: 'Direct executive summary.',
          key_strengths: ['Great utility usage'],
          critical_flaws: ['Poor crosshair discipline'],
        },
        evidence: [],
        created_at: '2026-10-14T09:00:00Z',
      } as any)
    );

    component.onGenerateReport();

    expect(component.reports().length).toBe(2);
    expect(component.reports()[0].id).toBe('direct-report-101');
    expect(component.reports()[0].summary).toBe('Direct executive summary.');
    expect(component.reports()[0].strengths).toContain('Great utility usage');
    expect(component.reports()[0].weaknesses).toContain('Poor crosshair discipline');
    expect(component.statusMessage()).toContain('éxito');
  });
});
