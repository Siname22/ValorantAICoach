import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApiClientService } from './api-client.service';

describe('Player region HTTP contract', () => {
  let api: ApiClientService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ApiClientService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends the selected region to report history and progression', () => {
    api.getCoachingReports('Alpha', 'EU1', 20, 'na').subscribe();
    const history = http.expectOne('/v1/players/Alpha/EU1/reports?limit=20&region=na');
    expect(history.request.method).toBe('GET');
    history.flush({ reports: [], count: 0 });

    api.getPlayerProgression('Alpha', 'EU1', 'na').subscribe();
    const progression = http.expectOne('/v1/players/Alpha/EU1/progression?region=na');
    expect(progression.request.method).toBe('GET');
    progression.flush({});
  });
});
