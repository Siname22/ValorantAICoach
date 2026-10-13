# ADR-015: Migración de Frontend a SPA Angular 19 con Diseño HUD Bento

## Estado
Aceptado (Sustituye a [ADR-014](ADR-014-streamlit-frontend.md))

## Contexto
El prototipo inicial de frontend implementado en Streamlit (ADR-014) permitió validar la integración con el backend y las capacidades analíticas de IA. Sin embargo, para una experiencia de usuario competitiva de nivel producción en esports, Streamlit presentaba limitaciones estructurales:
1. Re-ejecución completa del script Python en cada interacción de usuario (`st.session_state`), lo que provocaba latencias perceptibles y pérdida de micro-interacciones.
2. Imposibilidad de cumplir con los estrictos estándares de accesibilidad **WCAG 2.2 AA** (contraste, navegación completa por teclado, regiones ARIA vivas, lectores de pantalla).
3. Sobrecarga de dependencias en el runtime de Python (21 paquetes pesados como Streamlit, Plotly, Pandas, Altair, PyArrow).
4. Carencia de un diseño temático inmersivo de esports con layout Bento Grid responsivo y tokens CSS adaptados al HUD de Valorant.

## Decisión
Se decide reemplazar completamente el frontend de Streamlit por una Single Page Application (SPA) moderna en **Angular 19**:
- **Arquitectura Standalone y Signals**: Componentes independientes sin `NgModules`, gestión de estado reactivo mediante signals y `ChangeDetectionStrategy.OnPush` para máximo rendimiento.
- **Cliente API fuertemente tipado**: Generado automáticamente a partir de `/openapi.json` de FastAPI, garantizando estricta paridad con los esquemas del backend sin DTOs manuales.
- **Diseño HUD Bento Grid**: Sistema de diseño basado en design tokens CSS (`--valorant-red`, `--hud-bg`, `--hud-border`, etc.) con cards bento modulares, gráficos SVG accesibles sin dependencias pesadas y micro-animaciones HUD.
- **Accesibilidad WCAG 2.2 AA**: Foco gestionado mediante `@angular/cdk/a11y`, skip-links, soporte nativo de alto contraste y `prefers-reduced-motion`, etiquetas y descripciones ARIA en todos los elementos interactivos.
- **Despliegue y Aislamiento**: Multi-stage build con Docker (Node 22-alpine para compilación y Nginx 1.27-alpine como servidor estático de producción), eliminando completamente Node.js y dependencias de UI del contenedor backend.

## Consecuencias
- **Positivas**:
  - Eliminación de 21 dependencias obsoletas en Python (`streamlit`, `pandas`, `plotly`, etc.), reduciendo sustancialmente el tamaño de las imágenes y la superficie de ataque.
  - Tiempos de carga casi instantáneos y navegación fluida entre vistas (HUD Dashboard, Búsqueda de Jugador, Informes de Coach, Análisis de Marcadores, Historial).
  - Cumplimiento verificado de accesibilidad WCAG 2.2 AA y rendimiento web óptimo.
  - Docker Compose simplificado: el servicio `frontend` ahora sirve la SPA en Nginx en el puerto 8080 (mapeado a 80 internamente).
- **Negativas**:
  - Requiere Node.js / npm para el desarrollo local del frontend en `frontend/web/`.
