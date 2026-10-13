import { TestBed } from '@angular/core/testing';
import { TokenService } from './token.service';

describe('TokenService', () => {
  let service: TokenService;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({});
    service = TestBed.inject(TokenService);
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('should be created and initial state should be unauthenticated', () => {
    expect(service).toBeTruthy();
    expect(service.hasToken()).toBeFalse();
    expect(service.getToken()).toBeNull();
  });

  it('should store token and update reactive signal and sessionStorage', () => {
    // Generate a valid mock JWT payload with future expiration
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const payload = btoa(JSON.stringify({ sub: 'testuser', is_admin: true, exp }));
    const mockToken = `${header}.${payload}.mockSignature`;

    service.setToken(mockToken);

    expect(service.hasToken()).toBeTrue();
    expect(service.getToken()).toBe(mockToken);
    expect(service.isAuthenticated()).toBeTrue();
    expect(service.currentUserSub()).toBe('testuser');
    expect(service.isAdmin()).toBeTrue();
    expect(service.isExpired()).toBeFalse();
  });

  it('should clear token and update state', () => {
    service.setToken('dummy.token.123');
    expect(service.hasToken()).toBeTrue();

    service.clearToken();
    expect(service.hasToken()).toBeFalse();
    expect(service.getToken()).toBeNull();
  });
});
