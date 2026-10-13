/**
 * Centralized Spanish dictionary for Valorant AI Coach.
 * Enables zero hardcoded UI strings and seamless future internationalization.
 */

export const I18N_ES = {
  app: {
    title: 'VALORANT AI COACH',
    tagline: 'HUD Táctico de Rendimiento y Coaching',
    skipLink: 'Saltar al contenido principal',
  },
  a11y: {
    skipToContent: 'Saltar al contenido principal',
  },
  nav: {
    ariaLabel: 'Navegación principal del HUD',
    summary: 'Resumen',
    matches: 'Partidas',
    reports: 'Informes del coach',
    vision: 'Marcador por imagen',
    account: 'Cuenta',
  },
  hero: {
    titlePrefix: 'Mejora tu',
    titleHighlight: 'próxima',
    titleSuffix: 'partida.',
    searchPlaceholder: 'Riot ID (ej. Mixwell#EU1 o TenZ#0001)',
    searchLabel: 'Buscar jugador por Riot ID',
    searchButton: 'ANALIZAR',
    searching: 'Analizando telemetría...',
    errorEmpty: 'Por favor, introduce tu Riot ID con formato Nombre#Tag.',
  },
  bento: {
    acsCard: {
      title: 'ACS Medio',
      subtitle: 'Puntuación de combate media en partidas recientes',
      diffPositive: '▲ por encima de la media de tu rango',
      diffNegative: '▼ por debajo de la media de tu rango',
      noData: 'Sin datos recientes',
    },
    planCard: {
      title: 'Plan de Mejora Táctica',
      subtitle: 'Recomendaciones prioritarias del orquestador de agentes',
      emptyState: 'No hay debilidades críticas registradas. ¡Sigue compitiendo!',
    },
    economyCard: {
      title: 'Economía por Ronda',
      subtitle: 'Gestión de créditos y ratio de compras (Full-Buy vs Eco)',
      tabRecent: 'Última partida',
      tabAggregate: 'Tendencia global',
      chartAccessibleSummary: 'Resumen de tendencia económica: gasto eficiente en rondas de compra completa con tasa de victoria del',
    },
    matchesCard: {
      title: 'Últimas Partidas',
      caption: 'Historial de partidas competitivas y telemetría de rendimiento',
      colResult: 'Resultado',
      colMap: 'Mapa',
      colAgent: 'Agente',
      colScore: 'Marcador',
      colKda: 'K / D / A',
      colAcs: 'ACS',
      victory: '▲ Victoria',
      defeat: '▼ Derrota',
      empty: 'No se encontraron partidas para este jugador.',
    },
    roleCoachCard: {
      title: 'Role Coach',
      subtitle: 'Diagnóstico de tu rol principal y cobertura de utilidad',
    },
    uploadCard: {
      title: 'Subida de Marcador',
      subtitle: 'Arrastra o selecciona la captura de fin de partida (PNG o JPG)',
      dropzone: 'Arrastra y suelta tu captura de pantalla aquí',
      formats: 'Formatos soportados: PNG, JPG, WEBP (hasta 10MB)',
      inputLabel: 'Archivo de imagen del marcador',
      button: 'Examinar archivo',
      uploading: 'Procesando captura con visión artificial...',
      success: 'Marcador analizado e incorporado al historial.',
      error: 'Error al procesar la imagen. Verifica que sea un marcador válido.',
    },
  },
  auth: {
    loginTitle: 'Iniciar sesión',
    registerTitle: 'Registro',
    username: 'Usuario',
    email: 'Email',
    password: 'Contraseña',
    registerSubmit: 'Registrarme',
    loginSubmit: 'Entrar',
    logout: 'Cerrar sesión',
  },
  status: {
    loading: 'Cargando datos...',
    errorGeneric: 'Se produjo un error al comunicar con el servidor.',
    notFound: 'No se encontró el perfil del jugador especificado.',
  },
} as const;

export type I18nDictionary = typeof I18N_ES;
