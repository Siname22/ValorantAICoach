import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { authInterceptor } from './auth.interceptor';
import { errorInterceptor } from './error.interceptor';
import { TokenService } from './token.service';

describe('Auth & Error Interceptors', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let tokenServiceSpy: jasmine.SpyObj<TokenService>;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {
    tokenServiceSpy = jasmine.createSpyObj('TokenService', [
      'getToken',
      'clearToken',
    ]);
    routerSpy = jasmine.createSpyObj('Router', ['navigate'], {
      url: '/partidas',
    });

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(
          withInterceptors([authInterceptor, errorInterceptor])
        ),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should attach Bearer token to request headers when token is present', () => {
    tokenServiceSpy.getToken.and.returnValue('mock-token-xyz');

    http.get('/api/test').subscribe();

    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.get('Authorization')).toBe('Bearer mock-token-xyz');
    req.flush({});
  });

  it('should not attach Authorization header when token is null', () => {
    tokenServiceSpy.getToken.and.returnValue(null);

    http.get('/api/test').subscribe();

    const req = httpMock.expectOne('/api/test');
    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({});
  });

  it('should clear token and redirect to /cuenta on 401 Unauthorized', () => {
    tokenServiceSpy.getToken.and.returnValue('mock-expired-token');

    http.get('/api/protected').subscribe({
      next: () => fail('Should have failed with 401'),
      error: (err) => {
        expect(err.status).toBe(401);
      },
    });

    const req = httpMock.expectOne('/api/protected');
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(tokenServiceSpy.clearToken).toHaveBeenCalled();
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/cuenta'], {
      queryParams: { returnUrl: '/partidas' },
    });
  });
});
