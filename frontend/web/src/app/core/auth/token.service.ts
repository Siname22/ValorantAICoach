/**
 * Token Service managing JWT authentication.
 *
 * Architecture Decision (Duda 1):
 * - Primary storage: Angular reactive signal in memory.
 * - Tab persistence: sessionStorage (isolated to current browser tab, cleared on close).
 * - Justification: Prevents permanent disk exposure (localStorage) while preserving
 *   user session across page reloads (F5) without requiring a backend refresh endpoint.
 */

import { Injectable, computed, signal } from '@angular/core';

export interface JwtPayload {
  readonly sub: string;
  readonly is_admin?: boolean;
  readonly exp?: number;
}

const SESSION_TOKEN_KEY = 'val_coach_auth_token';

@Injectable({
  providedIn: 'root',
})
export class TokenService {
  private readonly tokenSignal = signal<string | null>(this.readInitialToken());

  readonly currentToken = this.tokenSignal.asReadonly();
  readonly isAuthenticated = computed(() => Boolean(this.tokenSignal()));

  readonly currentUserSub = computed(() => {
    const payload = this.getPayload();
    return payload ? payload.sub : null;
  });

  readonly isAdmin = computed(() => {
    const payload = this.getPayload();
    return Boolean(payload?.is_admin);
  });

  setToken(token: string): void {
    this.tokenSignal.set(token);
    try {
      sessionStorage.setItem(SESSION_TOKEN_KEY, token);
    } catch {
      // In restricted contexts, gracefully fallback to memory-only
    }
  }

  getToken(): string | null {
    return this.tokenSignal();
  }

  hasToken(): boolean {
    return Boolean(this.tokenSignal());
  }

  clearToken(): void {
    this.tokenSignal.set(null);
    try {
      sessionStorage.removeItem(SESSION_TOKEN_KEY);
    } catch {
      // No-op
    }
  }

  getPayload(): JwtPayload | null {
    const token = this.tokenSignal();
    if (!token) return null;
    try {
      const parts = token.split('.');
      if (parts.length < 2) return null;
      const base64Url = parts[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload) as JwtPayload;
    } catch {
      return null;
    }
  }

  isExpired(): boolean {
    const payload = this.getPayload();
    if (!payload?.exp) return false;
    return Date.now() >= payload.exp * 1000;
  }

  private readInitialToken(): string | null {
    try {
      const token = sessionStorage.getItem(SESSION_TOKEN_KEY);
      if (token) {
        // If expired, discard immediately
        const parts = token.split('.');
        if (parts.length >= 2) {
          const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
          const payload = JSON.parse(atob(base64)) as JwtPayload;
          if (payload.exp && Date.now() >= payload.exp * 1000) {
            sessionStorage.removeItem(SESSION_TOKEN_KEY);
            return null;
          }
        }
      }
      return token;
    } catch {
      return null;
    }
  }
}
