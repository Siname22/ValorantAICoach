import { inject } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  CanActivateFn,
  Router,
  RouterStateSnapshot,
} from '@angular/router';
import { TokenService } from './token.service';

export const authGuard: CanActivateFn = (
  _route: ActivatedRouteSnapshot,
  state: RouterStateSnapshot
) => {
  const tokenService = inject(TokenService);
  const router = inject(Router);

  if (tokenService.hasToken() && !tokenService.isExpired()) {
    return true;
  }

  // Not authenticated or token expired: redirect to /cuenta
  return router.createUrlTree(['/cuenta'], {
    queryParams: { returnUrl: state.url },
  });
};
