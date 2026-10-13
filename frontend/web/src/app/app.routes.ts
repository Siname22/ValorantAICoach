import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'resumen',
  },
  {
    path: 'resumen',
    loadComponent: () =>
      import('./features/summary/summary.component').then(
        (m) => m.SummaryComponent
      ),
    title: 'Resumen · Valorant AI Coach',
  },
  {
    path: 'partidas',
    loadComponent: () =>
      import('./features/matches/matches.component').then(
        (m) => m.MatchesComponent
      ),
    title: 'Partidas · Valorant AI Coach',
  },
  {
    path: 'informes',
    loadComponent: () =>
      import('./features/reports/reports.component').then(
        (m) => m.ReportsComponent
      ),
    title: 'Informes del Coach · Valorant AI Coach',
  },
  {
    path: 'marcador',
    loadComponent: () =>
      import('./features/vision/vision.component').then(
        (m) => m.VisionComponent
      ),
    title: 'Marcador por Imagen · Valorant AI Coach',
  },
  {
    path: 'cuenta',
    loadComponent: () =>
      import('./features/account/account.component').then(
        (m) => m.AccountComponent
      ),
    title: 'Cuenta · Valorant AI Coach',
  },
  {
    path: '**',
    redirectTo: 'resumen',
  },
];
