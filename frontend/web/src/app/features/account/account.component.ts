import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { BentoCardComponent } from '../../shared/ui/bento-card/bento-card.component';
import { I18N_ES } from '../../core/i18n/es';
import { TokenService } from '../../core/auth/token.service';
import { ApiClientService } from '../../core/api/api-client.service';
import { LinkedAccountResponse, UserResponse } from '../../core/api/api-models';

@Component({
  selector: 'app-account',
  standalone: true,
  imports: [CommonModule, FormsModule, BentoCardComponent],
  template: `
    <div class="account-page">
      <app-bento-card span="full" customId="account-title">
        <h1 id="account-title" class="page-title">{{ i18n.nav.account }}</h1>
        <p class="page-subtitle">
          Gestiona tu perfil, credenciales de acceso y cuentas de Riot Games vinculadas.
        </p>
      </app-bento-card>

      @if (tokenService.hasToken()) {
        <!-- User Profile Card -->
        <app-bento-card span="full" title="Sesión Activa" subtitle="Información de tu cuenta de usuario">
          <div class="profile-card">
            @if (user()) {
              <div class="profile-details">
                <p><strong>Usuario:</strong> {{ user()?.username }}</p>
                <p><strong>Email:</strong> {{ user()?.email }}</p>
                <p><strong>Rol:</strong> {{ user()?.is_admin ? 'Administrador' : 'Jugador' }}</p>
                <p><strong>Riot ID principal:</strong> {{ user()?.riot_id || 'Ninguno vinculado' }}</p>
              </div>
            } @else {
              <p>Cargando información del perfil...</p>
            }

            <button type="button" class="btn-primary logout-btn" (click)="onLogout()">
              {{ i18n.auth.logout }}
            </button>
          </div>
        </app-bento-card>

        <!-- Linked Riot Accounts Card -->
        <app-bento-card span="full" title="Cuentas Riot Vinculadas" subtitle="Tus perfiles de jugador asociados">
          <div class="linked-accounts-section">
            @if (linkedAccounts().length > 0) {
              <ul class="accounts-list" role="list">
                @for (acc of linkedAccounts(); track acc.id) {
                  <li class="account-item">
                    <div class="account-item-info">
                      <span class="account-name">{{ acc.game_name }}#{{ acc.tag_line }}</span>
                      @if (acc.is_primary) {
                        <span class="badge-primary">Principal</span>
                      }
                    </div>
                    <button
                      type="button"
                      class="btn-unlink"
                      (click)="unlinkAccount(acc.id)"
                      [disabled]="actionLoading()"
                      [attr.aria-label]="'Desvincular ' + acc.game_name + '#' + acc.tag_line"
                    >
                      Desvincular
                    </button>
                  </li>
                }
              </ul>
            } @else {
              <p class="no-accounts">No tienes cuentas Riot vinculadas actualmente.</p>
            }

            <!-- Form to Link a new Riot Account -->
            <form class="link-form" (ngSubmit)="linkNewAccount()">
              <h2 class="link-form-title">Vincular nuevo Riot ID</h2>
              <div class="form-row">
                <div class="input-field">
                  <label for="link-game-name" class="input-label">Nombre en el juego</label>
                  <input
                    id="link-game-name"
                    name="gameName"
                    type="text"
                    [(ngModel)]="linkGameName"
                    class="form-input"
                    placeholder="Ej. TenZ"
                    required
                  />
                </div>
                <div class="input-field">
                  <label for="link-tag-line" class="input-label">Lema (Tag)</label>
                  <input
                    id="link-tag-line"
                    name="tagLine"
                    type="text"
                    [(ngModel)]="linkTagLine"
                    class="form-input"
                    placeholder="Ej. 0001"
                    required
                  />
                </div>
              </div>

              <div class="checkbox-field">
                <input
                  id="link-is-primary"
                  name="isPrimary"
                  type="checkbox"
                  [(ngModel)]="linkIsPrimary"
                  class="form-checkbox"
                />
                <label for="link-is-primary" class="checkbox-label">Establecer como cuenta principal</label>
              </div>

              @if (linkError()) {
                <p class="error-msg" role="alert" aria-live="polite">{{ linkError() }}</p>
              }

              @if (linkSuccess()) {
                <p class="success-msg" role="status" aria-live="polite">{{ linkSuccess() }}</p>
              }

              <button type="submit" class="btn-primary" [disabled]="actionLoading()">
                {{ actionLoading() ? 'Vinculando...' : 'Vincular Riot ID' }}
              </button>
            </form>
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

            <form
              id="panel-auth"
              role="tabpanel"
              [attr.aria-labelledby]="isRegisterMode() ? 'tab-register' : 'tab-login'"
              (ngSubmit)="onSubmit()"
              class="auth-form"
            >
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
    .linked-accounts-section {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .accounts-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .account-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background-color: var(--color-bg-page);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 12px 16px;
    }
    .account-item-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .account-name {
      font-family: var(--font-heading);
      font-weight: 600;
      font-size: 16px;
    }
    .badge-primary {
      background-color: var(--color-primary);
      color: var(--color-bg-page);
      font-size: 12px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: var(--radius-xs);
    }
    .btn-unlink {
      background: transparent;
      border: 1px solid var(--color-loss);
      color: var(--color-loss);
      font-size: 13px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: var(--radius-xs);
      cursor: pointer;
      min-height: 44px;
      transition: background-color var(--transition-fast), color var(--transition-fast);
    }
    .btn-unlink:hover {
      background-color: rgba(255, 138, 148, 0.1);
    }
    .btn-unlink:focus-visible {
      outline: 3px solid var(--color-focus);
      outline-offset: 3px;
    }
    .no-accounts {
      color: var(--color-text-secondary);
      font-size: 14px;
    }
    .link-form {
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--color-border);
    }
    .link-form-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-text);
      margin: 0;
    }
    .form-row {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }
    .form-row .input-field {
      flex: 1;
      min-width: 200px;
    }
    .checkbox-field {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 44px;
    }
    .form-checkbox {
      width: 20px;
      height: 20px;
      accent-color: var(--color-primary);
      cursor: pointer;
    }
    .checkbox-label {
      font-size: 14px;
      cursor: pointer;
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
export class AccountComponent implements OnInit {
  readonly tokenService = inject(TokenService);
  private readonly api = inject(ApiClientService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly i18n = I18N_ES;

  readonly isRegisterMode = signal(false);
  readonly loading = signal(false);
  readonly actionLoading = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');
  readonly linkError = signal('');
  readonly linkSuccess = signal('');
  readonly user = signal<UserResponse | null>(null);
  readonly linkedAccounts = signal<LinkedAccountResponse[]>([]);

  username = '';
  email = '';
  password = '';

  linkGameName = '';
  linkTagLine = '';
  linkIsPrimary = true;

  ngOnInit(): void {
    if (this.tokenService.hasToken()) {
      this.loadUserData();
    }
  }

  setRegisterMode(val: boolean): void {
    this.isRegisterMode.set(val);
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  loadUserData(): void {
    this.api.getAuthMe().subscribe({
      next: (u) => {
        this.user.set(u);
        this.loadLinkedAccounts();
      },
      error: () => this.tokenService.clearToken()
    });
  }

  loadLinkedAccounts(): void {
    this.api.getLinkedAccounts().subscribe({
      next: (accs) => this.linkedAccounts.set(accs),
      error: () => {}
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
          this.loadUserData();

          // Redirect if returnUrl was passed
          const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
          if (returnUrl) {
            this.router.navigateByUrl(returnUrl);
          }
        },
        error: (err: { error?: { detail?: string } }) => {
          this.loading.set(false);
          this.errorMessage.set(err?.error?.detail || 'Credenciales incorrectas.');
        }
      });
    }
  }

  linkNewAccount(): void {
    if (!this.linkGameName.trim() || !this.linkTagLine.trim()) {
      this.linkError.set('Introduce tanto el nombre como el lema.');
      return;
    }

    this.actionLoading.set(true);
    this.linkError.set('');
    this.linkSuccess.set('');

    this.api.linkAccount({
      game_name: this.linkGameName.trim(),
      tag_line: this.linkTagLine.trim(),
      is_primary: this.linkIsPrimary
    }).subscribe({
      next: () => {
        this.actionLoading.set(false);
        this.linkSuccess.set('Cuenta vinculada correctamente.');
        this.linkGameName = '';
        this.linkTagLine = '';
        this.loadUserData();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.actionLoading.set(false);
        this.linkError.set(err?.error?.detail || 'Error al vincular cuenta.');
      }
    });
  }

  unlinkAccount(accountId: string): void {
    this.actionLoading.set(true);
    this.api.unlinkAccount(accountId).subscribe({
      next: () => {
        this.actionLoading.set(false);
        this.loadUserData();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.actionLoading.set(false);
        this.linkError.set(err?.error?.detail || 'Error al desvincular cuenta.');
      }
    });
  }

  onLogout(): void {
    this.tokenService.clearToken();
    this.user.set(null);
    this.linkedAccounts.set([]);
  }
}
