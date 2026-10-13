import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { I18N_ES } from '../../../core/i18n/es';

interface NavItem {
  readonly path: string;
  readonly label: string;
  readonly icon: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <aside class="sidebar-container" aria-label="Panel lateral">
      <div class="sidebar-brand">
        <div class="brand-badge" aria-hidden="true">V</div>
        <div class="brand-text">
          <span class="brand-title">{{ i18n.app.title }}</span>
          <span class="brand-sub">HUD BENTO</span>
        </div>
      </div>

      <nav class="sidebar-nav" [attr.aria-label]="i18n.nav.ariaLabel">
        <ul class="nav-list" role="list">
          @for (item of navItems; track item.path) {
            <li class="nav-item">
              <a
                [routerLink]="item.path"
                routerLinkActive="active"
                [routerLinkActiveOptions]="{ exact: item.path === '/resumen' }"
                #rla="routerLinkActive"
                [attr.aria-current]="rla.isActive ? 'page' : null"
                class="nav-link"
              >
                <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
                <span class="nav-label">{{ item.label }}</span>
              </a>
            </li>
          }
        </ul>
      </nav>

      <div class="sidebar-footer">
        <div class="status-indicator" role="status" aria-live="polite">
          <span class="status-dot" aria-hidden="true"></span>
          <span class="status-text">Backend Activo</span>
        </div>
      </div>
    </aside>
  `,
  styles: [`
    :host {
      display: block;
    }

    .sidebar-container {
      width: var(--sidebar-width);
      background-color: var(--color-bg-sidebar);
      border-right: 1px solid var(--color-border);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding: 24px 16px;
      gap: 32px;
    }

    .sidebar-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 8px;
    }

    .brand-badge {
      width: 36px;
      height: 36px;
      background: var(--color-action-primary);
      color: var(--color-action-text);
      font-family: var(--font-family-display);
      font-weight: 700;
      font-size: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      clip-path: polygon(0 0, 85% 0, 100% 15%, 100% 100%, 0 100%);
    }

    .brand-text {
      display: flex;
      flex-direction: column;
    }

    .brand-title {
      font-family: var(--font-family-display);
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--color-text-primary);
    }

    .brand-sub {
      font-size: 11px;
      letter-spacing: 0.1em;
      color: var(--color-text-secondary);
      text-transform: uppercase;
    }

    .sidebar-nav {
      flex: 1;
    }

    .nav-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .nav-link {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-radius: var(--radius-nav);
      color: var(--color-text-secondary);
      font-family: var(--font-family-display);
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.02em;
      transition: background-color var(--transition-fast), color var(--transition-fast);
      min-height: var(--min-touch-target);
    }

    .nav-link:hover {
      background-color: var(--color-bg-card);
      color: var(--color-text-primary);
    }

    /* Active page navigation indicator (Design spec: aria-current="page" and lime background) */
    .nav-link.active,
    .nav-link[aria-current="page"] {
      background-color: var(--color-action-primary);
      color: var(--color-action-text);
      font-weight: 700;
    }

    .nav-icon {
      font-size: 16px;
    }

    .sidebar-footer {
      border-top: 1px solid var(--color-border);
      padding-top: 16px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      font-size: 12px;
      color: var(--color-text-secondary);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--color-status-victory);
    }

    /* Responsive: below ~900px sidebar stacks on top */
    @media (max-width: 900px) {
      .sidebar-container {
        width: 100%;
        min-height: auto;
        border-right: none;
        border-bottom: 1px solid var(--color-border);
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        padding: 16px;
        gap: 16px;
      }

      .nav-list {
        flex-direction: row;
        gap: 6px;
        overflow-x: auto;
      }

      .sidebar-footer {
        display: none;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarComponent {
  readonly i18n = I18N_ES;

  readonly navItems: readonly NavItem[] = [
    { path: '/resumen', label: I18N_ES.nav.summary, icon: '⊞' },
    { path: '/partidas', label: I18N_ES.nav.matches, icon: '⚔' },
    { path: '/informes', label: I18N_ES.nav.reports, icon: '📋' },
    { path: '/marcador', label: I18N_ES.nav.vision, icon: '📷' },
    { path: '/cuenta', label: I18N_ES.nav.account, icon: '👤' },
  ];
}
