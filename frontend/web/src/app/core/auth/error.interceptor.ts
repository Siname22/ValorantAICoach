/**
 * Error Interceptor: intercepts 401 Unauthorized responses, clears session,
 * and routes user gracefully to account/login with returnUrl query parameter.
 */

import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { TokenService } from './token.service';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const tokenService = inject(TokenService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        tokenService.clearToken();
        const currentUrl = router.url;
        if (!currentUrl.includes('/cuenta')) {
          router.navigate(['/cuenta'], {
            queryParams: { returnUrl: currentUrl }
          });
        }
      }
      return throwError(() => error);
    })
  );
};
