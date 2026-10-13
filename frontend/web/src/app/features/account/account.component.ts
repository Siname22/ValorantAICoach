import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { TokenService } from '../../core/auth/token.service';
import { ApiClientService } from '../../core/api/api-client.service';
import { UserResponse } from '../../core/api/api-models';

@Component({
  selector: 'app-account',
  standalone: true,
  imports: [CommonModule, FormsModule, BentoCardComponent],
  template: `
    <div class="account-page">
      <app-bento-card span="full" customId="account-title">
        <h1 id="account-title" class="page-title">{{ i18n.nav.account }}</h1>
        <p class="page-subtitle">
          Gestiona tu perfil, credenciales de acceso y preferencias de análisis táctico.
        </p>
      </app-bento-card>

      @if (tokenService.hasToken()) {
        <!-- User Profile Card -->
        <app-bento-card span="full" title="Sesión Activa" subtitle="Información de tu cuenta">
          <div class="profile-card">
            @if (user()) {
              <div class="profile-details">
                <p><strong>Usuario:</strong> {{ user()?.username }}</p>
                <p><strong>Email:</strong> {{ user()?.email }}</p>
                <p><strong>Rol:</strong> {{ user()?.is_admin ? 'Administrador' : 'Jugador' }}</p>
                <p><strong>Riot ID vinculado:</strong> {{ user()?.riot_id || 'Ninguno' }}</p>
              </div>
            } @else {
              <p>Cargando detalles de la cuenta...</p>
            }

            <button type="button" class="btn-primary logout-btn" (click)="onLogout()">
              {{ i18n.auth.logout }}
            </button>
          </div>
        </app-bento-card>
      } @else {
        <!-- Auth Tabs: Login / Register -->
        <div class="auth-grid">
          <app-bento-card [title]="isRegisterMode() ? i18n.auth.registerTitle : i18n.auth.loginTitle">
            <div class="auth-tabs" role="tablist" aria-label="Opciones de autenticación">
              <button
                type="button"
                role="tab"
                [attr.aria-selected]="!isRegisterMode()"
                id="tab-login"
                aria-controls="panel-auth"
                class="tab-btn"
                [class.active]="!isRegisterMode()"
                (click)="setRegisterMode(false)"
              >
                {{ i18n.auth.loginTitle }}
              </button>
              <button
                type="button"
                role="tab"
                [attr.aria-selected]="isRegisterMode()"
                id="tab-register"
                aria-controls="panel-auth"
                class="tab-btn"
                [class.active]="isRegisterMode()"
                (click)="setRegisterMode(true)"
              >
                {{ i18n.auth.registerTitle }}
              </button>
            </div>

            <form id="panel-auth" role="tabpanel" [attr.aria-labelledby]="isRegisterMode() ? 'tab-register' : 'tab-login'" (ngSubmit)="onSubmit()" class="auth-form">
              <div class="input-field">
                <label for="auth-username" class="input-label">{{ i18n.auth.username }}</label>
                <input
                  id="auth-username"
                  name="username"
                  type="text"
                  [(ngModel)]="username"
                  class="form-input"
                  required
                  autocomplete="username"
                />
              </div>

              @if (isRegisterMode()) {
                <div class="input-field">
                  <label for="auth-email" class="input-label">{{ i18n.auth.email }}</label>
                  <input
                    id="auth-email"
                    name="email"
                    type="email"
                    [(ngModel)]="email"
                    class="form-input"
                    required
                    autocomplete="email"
                  />
                </div>
              }

              <div class="input-field">
                <label for="auth-password" class="input-label">{{ i18n.auth.password }}</label>
                <input
                  id="auth-password"
                  name="password"
                  type="password"
                  [(ngModel)]="password"
                  class="form-input"
                  required
                  autocomplete="current-password"
                />
              </div>

              @if (errorMessage()) {
                <p class="error-msg" role="alert" aria-live="polite">
                  {{ errorMessage() }}
                </p>
              }

              @if (successMessage()) {
                <p class="success-msg" role="status" aria-live="polite">
                  {{ successMessage() }}
                </p>
              }

              <button type="submit" class="btn-primary submit-btn" [disabled]="loading()">
                {{ loading() ? 'Procesando...' : (isRegisterMode() ? i18n.auth.registerSubmit : i18n.auth.loginSubmit) }}
              </button>
            </form>
          </app-bento-card>
        </div>
      }
    </div>
  `,
  styles: [`
    .account-page {
      display: flex;
      flex-direction: column;
      gap: var(--main-gap);
    }
    .page-title {
      font-size: var(--font-size-h1);
      margin-bottom: 8px;
    }
    .page-subtitle {
      color: var(--color-text-secondary);
      font-size: 14px;
    }
    .profile-card {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .profile-details p {
      margin-bottom: 8px;
      font-size: 15px;
    }
    .logout-btn {
      align-self: flex-start;
      margin-top: 12px;
    }
    .auth-grid {
      max-width: 500px;
    }
    .auth-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--color-border);
      padding-bottom: 8px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--color-text-secondary);
      font-family: var(--font-body);
      font-size: 15px;
      font-weight: 600;
      padding: 8px 16px;
      cursor: pointer;
      border-radius: var(--radius-xs);
      transition: color var(--transition-fast), background-color var(--transition-fast);
      min-height: 44px;
      min-width: 44px;
    }
    .tab-btn.active {
      color: var(--color-bg-page);
      background-color: var(--color-primary);
    }
    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .form-input {
      background-color: var(--color-bg-page);
      border: 1px solid var(--color-input-border);
      color: var(--color-text);
      font-family: var(--font-body);
      font-size: 15px;
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      min-height: 44px;
    }
    .form-input:focus {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
    }
    .submit-btn {
      margin-top: 8px;
      width: 100%;
    }
    .error-msg {
      color: var(--color-loss);
      font-size: 14px;
    }
    .success-msg {
      color: var(--color-win);
      font-size: 14px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccountComponent {
  readonly tokenService = inject(TokenService);
  private readonly api = inject(ApiClientService);
  readonly i18n = I18N_ES;

  readonly isRegisterMode = signal(false);
  readonly loading = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  readonly user = signal<UserResponse | null>(null);

  username = '';
  email = '';
  password = '';

  constructor() {
    if (this.tokenService.hasToken()) {
      this.loadCurrentUser();
    }
  }

  setRegisterMode(val: boolean): void {
    this.isRegisterMode.set(val);
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  loadCurrentUser(): void {
    this.api.getAuthMe().subscribe({
      next: (u) => this.user.set(u),
      error: () => this.tokenService.clearToken()
    });
  }

  onSubmit(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
    this.loading.set(true);

    if (this.isRegisterMode()) {
      this.api.postAuthRegister({
        username: this.username,
        email: this.email,
        password: this.password
      }).subscribe({
        next: () => {
          this.loading.set(false);
          this.successMessage.set('Registro exitoso. Ya puedes iniciar sesión.');
          this.setRegisterMode(false);
        },
        error: (err: { error?: { detail?: string } }) => {
          this.loading.set(false);
          this.errorMessage.set(err?.error?.detail || 'Error al registrar usuario.');
        }
      });
    } else {
      this.api.postAuthLogin({
        username: this.username,
        password: this.password
      }).subscribe({
        next: (token) => {
          this.loading.set(false);
          this.tokenService.setToken(token.access_token);
          this.loadCurrentUser();
        },
        error: (err: { error?: { detail?: string } }) => {
          this.loading.set(false);
          this.errorMessage.set(err?.error?.detail || 'Credenciales incorrectas.');
        }
      });
    }
  }

  onLogout(): void {
    this.tokenService.clearToken();
    this.user.set(null);
  }
}
