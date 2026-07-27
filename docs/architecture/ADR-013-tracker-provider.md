# ADR-013: Tracker Provider (Tracker.gg)

## Estado

Aceptado

## Contexto

El Provider SDK v1 (ADR-011) estableció la infraestructura base para integrar servicios externos: `BaseProvider`, `BaseHTTPClient`, `ProviderConfig` y la jerarquía de excepciones `ProviderError`. El paquete `backend/providers/tracker/` existía como scaffold parcial. Este ADR documenta la conversión de dicho scaffold en un proveedor completamente funcional para la API pública de Tracker.gg (Valorant), sin modificar el framework de agentes ni el Provider SDK.

## Decisiones

### 1. Cliente HTTP dedicado (`TrackerHTTPClient`)

- **Decisión**: Se crea `TrackerHTTPClient`, que hereda de `BaseHTTPClient` y reutiliza íntegramente su gestión de sesiones (`httpx.AsyncClient` perezoso y reutilizable), timeouts, reintentos con *exponential backoff* y logging de peticiones. El cliente añade únicamente dos responsabilidades específicas: la autenticación mediante el header `TRN-Api-Key` (el header propietario de Tracker.gg, distinto del `X-API-Key` genérico del SDK) y el manejo enriquecido del HTTP 429.
- **Justificación**: Evita duplicar lógica del `BaseClient` — el único punto de extensión sobrescrito es `_handle_error_response`, el hook diseñado para ello.

### 2. Autenticación por API Key desde variables de entorno

- **Decisión**: La clave se obtiene exclusivamente de `TRACKER_API_KEY` (o `.env`) a través de `TrackerConfig`, que hereda de `ProviderConfig` con `env_prefix="TRACKER_"`. El campo `api_key` es obligatorio: instanciar la configuración sin clave falla en tiempo de arranque, nunca en tiempo de petición.
- **Justificación**: Cumple la política del proyecto de no *hardcodear* secretos, y falla rápido con un error de validación claro.

### 3. Rate limiting con `Retry-After`

- **Decisión**: Ante un HTTP 429, el cliente lanza `TrackerRateLimitError` con el valor de `Retry-After` parseado (soporta formato *delta-seconds* y *HTTP-date*, con tope de 30 s). Como esta excepción hereda de `RateLimitError` base, el bucle de reintentos del `BaseHTTPClient` la reintenta automáticamente; si los reintentos se agotan, la excepción propagada expone `retry_after` para que las capas superiores (agentes, schedulers) programen el siguiente intento con precisión.
- **Justificación**: Aprovecha el retry automático ya existente sin duplicar bucles, y añade la semántica específica que la API de Tracker.gg proporciona.

### 4. Endpoints encapsulados

- **Decisión**: `TrackerProvider` expone métodos tipados: `get_player` / `get_player_profile` (Player Profile), `get_match_history` / `get_recent_matches` (Match History), `get_player_stats` / `get_lifetime_stats` (Lifetime Stats), más `get_season_stats`, `get_weapon_stats` y `get_agent_stats` derivados de los segmentos del perfil. Ningún consumidor construye URLs ni parsea JSON crudo.
- **Justificación**: El proveedor es la única frontera con el formato de Tracker.gg; los agentes trabajan solo con modelos de dominio.

### 5. Modelos Pydantic completos

- **Decisión**: Se modelan `Player`, `PlayerIdentity`, `SeasonStats`, `MatchSummary`/`MatchHistory`, `WeaponStats`, `AgentStats`, `Rank`, `StatValue` y `LifetimeStats`, todos con alias *camelCase* (`populate_by_name=True`) para mapear el JSON de la API sin sacrificar el naming *snake_case* interno. Se eliminó el wrapper genérico `TrackerResponse` basado en `dict[str, Any]`.
- **Justificación**: El requisito explícito es no usar diccionarios genéricos cuando la estructura es conocida; los alias mantienen compatibilidad bidireccional de serialización.

### 6. Jerarquía de excepciones específica

- **Decisión**: `TrackerError` (base), `TrackerAuthenticationError` (401/403), `TrackerNotFound` (404), `TrackerRateLimitError` (429, con `retry_after`) y `TrackerServerError` (5xx). Cada una hereda simultáneamente de `TrackerError` y de su equivalente del SDK, de modo que un `except RateLimitError` genérico sigue capturándolas. Se mantiene el alias `TrackerRateLimit` por compatibilidad con imports existentes.
- **Justificación**: Doble herencia = manejo granular por proveedor sin romper el manejo polimórfico del SDK.

### 7. Logging

- **Decisión**: Todo el logging usa `logging.getLogger(__name__)`, integrado con la observabilidad del framework v1.2. Las API Keys nunca se registran.

## Configuración

Variables de entorno (ver `.env.example`):

| Variable | Obligatoria | Default | Descripción |
|---|---|---|---|
| `TRACKER_API_KEY` | Sí | — | API Key de Tracker.gg (solicitar en https://tracker.gg/developers) |
| `TRACKER_BASE_URL` | No | `https://public-api.tracker.gg/v2/valorant/standard` | URL base de la API |
| `TRACKER_TIMEOUT` | No | `30.0` | Timeout por petición (s) |
| `TRACKER_RETRIES` | No | `3` | Reintentos ante fallos transitorios |

## Ejemplo de uso

```python
from backend.providers.tracker import TrackerConfig, TrackerProvider
from backend.providers.tracker.exceptions import (
    TrackerNotFound,
    TrackerRateLimitError,
)

config = TrackerConfig()  # lee TRACKER_API_KEY del entorno / .env
provider = TrackerProvider(config)

try:
    profile = await provider.get_player_profile("riot", "Player#123")
    stats = await provider.get_lifetime_stats("riot", "Player#123")
    history = await provider.get_match_history("riot", "Player#123")
    print(profile.identity.platform_user_handle, stats.kd_ratio.display_value)
    for match in history.matches:
        print(match.map_name, match.result, match.kills)
except TrackerNotFound:
    print("Jugador no encontrado")
except TrackerRateLimitError as e:
    print(f"Rate limited; reintentar en {e.retry_after} segundos")
finally:
    await provider.close()
```

## Consecuencias

- **Positivas**: los agentes consumen datos de Valorant mediante modelos tipados y estables; el manejo de 429 con `Retry-After` hace al sistema resiliente frente a los límites estrictos de la API pública de Tracker.gg; la cobertura de tests (26 casos con `respx`) protege el contrato del proveedor.
- **Negativas**: el esquema de segmentos de Tracker.gg no está documentado oficialmente de forma exhaustiva; si la API cambia el formato de los segmentos, los parsers internos (`_parse_*`) deberán ajustarse, aunque el contrato público (modelos) quedaría intacto.
