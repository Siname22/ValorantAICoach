import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { authGuard } from './auth.guard';
import { TokenService } from './token.service';

describe('authGuard', () => {
  let tokenServiceSpy: jasmine.SpyObj<TokenService>;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {
    tokenServiceSpy = jasmine.createSpyObj('TokenService', [
      'hasToken',
      'isExpired',
    ]);
    routerSpy = jasmine.createSpyObj('Router', ['createUrlTree']);

    TestBed.configureTestingModule({
      providers: [
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    });
  });

  it('should allow access when token is present and not expired', () => {
    tokenServiceSpy.hasToken.and.returnValue(true);
    tokenServiceSpy.isExpired.and.returnValue(false);

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as ActivatedRouteSnapshot, { url: '/partidas' } as RouterStateSnapshot)
    );

    expect(result).toBeTrue();
  });

  it('should redirect to /cuenta with returnUrl when token is absent', () => {
    tokenServiceSpy.hasToken.and.returnValue(false);
    tokenServiceSpy.isExpired.and.returnValue(false);
    const mockTree = {} as UrlTree;
    routerSpy.createUrlTree.and.returnValue(mockTree);

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as ActivatedRouteSnapshot, { url: '/partidas' } as RouterStateSnapshot)
    );

    expect(routerSpy.createUrlTree).toHaveBeenCalledWith(['/cuenta'], {
      queryParams: { returnUrl: '/partidas' },
    });
    expect(result).toBe(mockTree);
  });
});
