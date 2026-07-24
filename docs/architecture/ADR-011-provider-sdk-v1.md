# ADR-011: Provider SDK v1.0

## Estado

Aceptado

## Contexto

Con la evolución del AI Agent Framework a la v1.2, el proyecto ValorantAICoach requiere una infraestructura robusta y escalable para integrar múltiples proveedores externos (Tracker.gg, Henrik API, Riot API, LLMs, OCR, etc.). La integración directa y ad-hoc de estos servicios llevaría a la duplicación de código, inconsistencias en el manejo de errores y dificultades en el testing. El objetivo de este ADR es definir la arquitectura del Provider SDK v1.0, que servirá como la base estandarizada para todos los proveedores futuros.

## Decisiones

### 1. Estructura de Paquetes Unificada

-   **Decisión**: Se ha establecido una estructura de paquetes bajo `backend/providers/`, con un subpaquete `base/` que contiene la infraestructura compartida y subpaquetes específicos para cada proveedor (ej. `tracker/`, `henrik/`, `llm/`).
-   **Justificación**: Esta organización sigue los principios de Clean Architecture y DDD, separando claramente la infraestructura base de las implementaciones concretas. Facilita la navegación del código y permite que cada proveedor crezca de forma independiente siguiendo el mismo patrón.

### 2. BaseProvider y BaseHTTPClient

-   **Decisión**: Se ha implementado una clase abstracta `BaseProvider` que define el contrato para todos los proveedores (`initialize`, `health_check`, `close`). Cada proveedor utiliza un `BaseHTTPClient` basado en `httpx.AsyncClient` para realizar peticiones HTTP.
-   **Justificación**: `BaseProvider` garantiza la consistencia en la interfaz de los proveedores, permitiendo que el sistema los trate de forma polimórfica. `BaseHTTPClient` centraliza la lógica compleja de comunicación HTTP, incluyendo reintentos con *exponential backoff*, manejo de timeouts, logging de peticiones y mapeo de errores HTTP a excepciones personalizadas del dominio.

### 3. Configuración mediante Pydantic Settings

-   **Decisión**: La configuración de los proveedores se gestiona a través de `ProviderConfig`, que hereda de `BaseSettings` de Pydantic. Cada proveedor puede extender esta configuración con sus propios parámetros.
-   **Justificación**: Pydantic Settings permite una gestión de configuración profesional, soportando variables de entorno, archivos `.env` y validación de tipos automática. Esto elimina el *hardcoding* de URLs y API Keys, facilitando el despliegue en diferentes entornos.

### 4. Jerarquía de Excepciones Personalizada

-   **Decisión**: Se ha creado una jerarquía de excepciones bajo `ProviderError`, incluyendo `HTTPProviderError`, `AuthenticationError`, `RateLimitError`, `NotFoundError`, `TimeoutError`, `ServerError` y `ConfigurationError`.
-   **Justificación**: Evitar el uso de excepciones genéricas permite un manejo de errores más preciso y granular en las capas superiores. Cada excepción HTTP captura el código de estado y el cuerpo de la respuesta para facilitar la depuración.

### 5. Integración con DependencyContainer

-   **Decisión**: El `DependencyContainer` ha sido actualizado para soportar la resolución de dependencias por tipo de clase (`resolve(Type[T])`). El Provider SDK se registra en este contenedor, permitiendo que los agentes y otros servicios soliciten proveedores sin conocer su implementación concreta.
-   **Justificación**: Esto refuerza el desacoplamiento y facilita el testing. Un agente puede solicitar un `TrackerProvider` y recibir una implementación real o un *mock* dependiendo de la configuración del contenedor.

### 6. Observabilidad Integrada

-   **Decisión**: Cada petición HTTP realizada a través de `BaseHTTPClient` registra automáticamente metadatos relevantes (Provider, Método, Endpoint, Tiempo, Código HTTP) utilizando el sistema de logging estándar, integrándose con la infraestructura de observabilidad de la v1.2.
-   **Justificación**: La visibilidad sobre las llamadas externas es crítica para el monitoreo del rendimiento y la resolución de problemas en sistemas distribuidos. Se ha tenido especial cuidado en nunca registrar API Keys o información sensible.

## Consecuencias

-   **Positivas**:
    -   **Escalabilidad**: Añadir un nuevo proveedor es ahora una tarea trivial que consiste en heredar de `BaseProvider` e implementar su lógica específica.
    -   **Robustez**: El manejo centralizado de reintentos y errores HTTP mejora la resiliencia del sistema frente a fallos externos.
    -   **Testabilidad**: La infraestructura está diseñada para ser fácilmente testeable mediante el uso de *mocks* (ej. `respx` para httpx).
    -   **Mantenibilidad**: El código compartido se encuentra en un solo lugar (`base/`), reduciendo el riesgo de bugs y facilitando las actualizaciones globales.

-   **Negativas**:
    -   **Abstracción Adicional**: Los desarrolladores deben familiarizarse con la estructura del SDK antes de implementar nuevos proveedores.

## Decisión Final

La arquitectura del Provider SDK v1.0 proporciona una base sólida, profesional y altamente extensible para la integración de servicios externos en ValorantAICoach. Sigue los mejores estándares de la industria y está preparada para escalar a decenas de proveedores manteniendo la calidad y la coherencia del sistema.
