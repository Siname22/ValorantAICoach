import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { VisionComponent } from './vision.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { of } from 'rxjs';

describe('VisionComponent', () => {
  let component: VisionComponent;
  let fixture: ComponentFixture<VisionComponent>;
  let apiSpy: jasmine.SpyObj<ApiClientService>;

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('ApiClientService', ['postVisionScoreboardAnalyze']);

    await TestBed.configureTestingModule({
      imports: [VisionComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ApiClientService, useValue: apiSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(VisionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the vision component', () => {
    expect(component).toBeTruthy();
  });

  it('should have accessible file input and native upload button', () => {
    const input: HTMLInputElement = fixture.nativeElement.querySelector('input[type="file"]');
    expect(input).toBeTruthy();
    expect(input.getAttribute('accept')).toContain('image/png');

    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button.upload-btn');
    expect(button).toBeTruthy();
  });

  it('should call postVisionScoreboardAnalyze when a file is analyzed', () => {
    const file = new File(['fake content'], 'test-scoreboard.png', { type: 'image/png' });
    component.selectedFile.set(file);
    component.selectedFileName.set(file.name);
    fixture.detectChanges();

    apiSpy.postVisionScoreboardAnalyze.and.returnValue(
      of({
        status: 'success',
        extracted_data: { players: [] },
      })
    );

    component.analyzeScoreboard();

    expect(apiSpy.postVisionScoreboardAnalyze).toHaveBeenCalled();
    expect(component.analysisResult()).toBeTruthy();
  });
});
