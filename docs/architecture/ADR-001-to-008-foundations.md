# ADR-001 a ADR-008: Decisiones Arquitectónicas Fundacionales (Compendio)

## Estado
Aceptado

## Contexto
Durante las fases iniciales de diseño y desarrollo de **Valorant AI Coach**, se adoptaron una serie de decisiones estructurales que determinan la arquitectura, el modelo de datos, la resiliencia operativa y la seguridad de la plataforma. Este compendio documenta formalmente las decisiones ADR-001 a ADR-008.

---

### ADR-001: Adopción de Python 3.12+ y Gestor de Paquetes `uv`
- **Decisión**: Utilizar Python 3.12 como versión base mínima del runtime y `uv` como gestor determinista de dependencias, entornos virtuales y compilación lockfile (`uv.lock`).
- **Justificación**: Rendimiento de resolución hasta 100x superior a `pip`, soporte nativo para proyectos multi-extra y control determinista en CI y Docker.
- **Consecuencias**: Todos los comandos de compilación y ejecución usan `uv run` y `uv sync`.

---

### ADR-002: Backend Headless con FastAPI y Arquitectura Limpia
- **Decisión**: Estructurar el backend como una API REST desacoplada mediante FastAPI, organizada en capas de Transporte (routers), Dominio/Servicios, y Almacenamiento/Adaptadores.
- **Justificación**: Permite desacoplar completamente la lógica de negocio de la interfaz de usuario, exponiendo endpoints tipados y autogenerando documentación OpenAPI (Swagger).
- **Consecuencias**: La interfaz de usuario no tiene acceso directo a la base de datos ni a los proveedores externos; todo el tráfico pasa por la API REST.

---

### ADR-003: Multi-Provider Data Aggregation con Fallback Transparente
- **Decisión**: Diseñar adaptadores abstractos para Riot Games API, HenrikDev y Tracker.gg con mecanismos de circuit breaking, cacheo defensivo y degradación elegante.
- **Justificación**: Las APIs de terceros en VALORANT presentan límites de cuota, incidencias temporales o acceso restringido por claves de producción.
- **Consecuencias**: El usuario final recibe datos normalizados independientemente de la fuente upstream activa.

---

### ADR-004: Persistencia con PostgreSQL 16 y Migraciones Lineales con Alembic
- **Decisión**: Utilizar PostgreSQL 16 en producción con SQLAlchemy 2.0 y control de esquemas mediante migraciones formales y lineales de Alembic.
- **Justificación**: Integridad referencial, índices concurrentes para consultas de partidas y trazabilidad histórica de esquemas.
- **Consecuencias**: Prohibición de DDL automático (`create_all`) en producción; el despliegue requiere ejecutar `alembic upgrade head`.

---

### ADR-005: Aislamiento Estricto de Contenedores y Dependencias (Backend vs Frontend)
- **Decisión**: Separar las imágenes de Docker (`docker/backend.Dockerfile` y `docker/frontend.Dockerfile`) con entornos virtuales independientes y usuarios no root (`appuser`).
- **Justificación**: El backend no debe cargar dependencias de interfaz gráfica (Streamlit, Plotly), y el frontend no debe tener dependencias de persistencia directa (SQLAlchemy, Alembic, psycopg).
- **Consecuencias**: Seguridad de mínimo privilegio y superficies de ataque minimizadas.

---

### ADR-006: Autenticación JWT y Cuentas Vinculadas de Riot
- **Decisión**: Implementar registro de usuarios con tokens Bearer JWT firmados con HS256 y hashing de contraseñas de alta seguridad. Vinculación multi-cuenta de identidades de Riot.
- **Justificación**: Proteger los endpoints que consumen cuotas de LLM o mutan el estado del jugador, permitiendo trazabilidad y perfiles primarios.
- **Consecuencias**: Requiere validación estricta de tokens con claims obligatorios (`sub`, `exp`, `iat`).

---

### ADR-007: Resiliencia de Gemini AI con Cadena de Modelos Fallback
- **Decisión**: Configurar una cadena automática de failover de 3 modelos de Google Gemini (`gemini-2.5-flash` → `gemini-2.5-flash-lite` → `gemini-3.5-flash`) con backoff exponencial.
- **Justificación**: Absorber saturaciones transitorias (HTTP 503, 429) y caídas de servicio sin interrumpir la sesión del jugador ni filtrar detalles técnicos.
- **Consecuencias**: Alta disponibilidad garantizada y verificada mediante suite de resiliencia automatizada.

---

### ADR-008: Ingesta de Marcadores por Visión Artificial y OCR Multimodal
- **Decisión**: Proveer endpoints para analizar capturas de pantalla de marcadores finales de VALORANT usando visión multimodal de Gemini, extrayendo resultados honestos y persistiendo las estadísticas en el historial.
- **Justificación**: Permite registrar partidas incluso cuando los proveedores de API no tienen indexada la partida o carecen de historial competitivo inmediato.
- **Consecuencias**: Requiere validación de tipos MIME de imagen (PNG, JPEG, WebP) y límites defensivos de tamaño (15MB).
