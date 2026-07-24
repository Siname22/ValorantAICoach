# ADR-010: AI Agent Framework v1.2 Enterprise Hardening

## Estado

Aceptado

## Contexto

El AI Agent Framework ha evolucionado a la versión 1.1, incorporando mejoras en la carga de prompts (`importlib.resources` y caché), una abstracción `BaseTool` para herramientas y hooks de ciclo de vida en `BaseAgent`. La auditoría técnica de la v1.1 identificó la necesidad de un mayor endurecimiento para entornos empresariales, centrándose en la inyección de dependencias, una gestión de memoria más eficiente, un registro de agentes mejorado y una observabilidad básica. El objetivo de la v1.2 es abordar estas áreas para preparar el framework para una integración más profunda y una escalabilidad robusta sin introducir frameworks externos complejos.

## Decisiones

### 1. Provider Layer Inicial

-   **Decisión**: Se ha creado una nueva estructura de carpetas `agents/shared/providers/` que contiene `base.py`, `models.py` y `exceptions.py`. Se ha definido una clase abstracta `BaseProvider` con propiedades `name`, `version` y métodos asíncronos `health_check()` y `execute()`. Se han creado modelos Pydantic (`ProviderConfig`, `LLMProviderConfig`, `ToolProviderConfig`, `ProviderHealth`) para la configuración y el estado de los proveedores.
-   **Justificación**: La necesidad de integrar diversos proveedores externos (LLMs, herramientas, datos) de manera uniforme y extensible es fundamental para un framework de agentes de IA. `BaseProvider` establece un contrato común que permite la intercambiabilidad de implementaciones de proveedores sin afectar la lógica del agente. Los modelos de configuración tipados facilitan la gestión de credenciales y parámetros específicos de cada proveedor, mientras que `health_check` es crucial para la resiliencia en producción. Esta abstracción prepara el terreno para la futura integración con proveedores reales como OpenAI, Gemini o modelos locales.
-   **Implicaciones**: Los agentes ahora pueden depender de una interfaz `BaseProvider` en lugar de implementaciones concretas. Esto fomenta el Principio de Inversión de Dependencias (DIP) y facilita el testing con proveedores *mock* o *fake*.

### 2. Dependency Injection Ligera

-   **Decisión**: Se ha creado `agents/shared/container.py` con una clase `DependencyContainer` simple. Este contenedor permite registrar y recuperar instancias de `BaseProvider`, `BaseMemory` y `BaseTool`. El constructor de `BaseAgent` ha sido modificado para aceptar inyecciones opcionales de `llm_provider`, `memory` y `tools`.
-   **Justificación**: La auditoría de la v1.1 señaló que los agentes creaban internamente sus dependencias, lo que dificultaba el testing unitario y la gestión de dependencias complejas. Un contenedor de DI ligero permite desacoplar la creación de objetos de su uso, facilitando la inyección de dependencias (ej. un `LLMProvider` específico o una `InMemoryMemory` para tests). Se optó por una implementación manual y ligera para evitar la sobrecarga de frameworks de DI externos, manteniendo la filosofía de 
simplicidad y mantenibilidad. El `DependencyContainer` es global para facilitar el acceso, pero su uso es opcional y permite la inyección directa cuando sea necesario.
-   **Implicaciones**: Mejora drástica en la testabilidad y flexibilidad de los agentes. Permite configurar diferentes proveedores o estrategias de memoria en tiempo de ejecución o para diferentes entornos.

### 3. Refactor AgentMemory

-   **Decisión**: Se ha creado un nuevo subpaquete `agents/shared/memory/` con `base.py` (definiendo la interfaz `BaseMemory` con métodos asíncronos `add()`, `get_all()`, `clear()`), `models.py` (conteniendo `MemoryEntry`) e `in_memory.py` (con la implementación `InMemoryMemory`). La implementación `InMemoryMemory` ahora utiliza una lista interna para almacenar `MemoryEntry` y evita la copia completa de la lista en cada operación `add()`, mejorando la eficiencia.
-   **Justificación**: La auditoría de la v1.1 identificó la ineficiencia de `AgentMemory` debido a la inmutabilidad de la lista interna, que resultaba en copias completas en cada adición. La introducción de `BaseMemory` como interfaz abstracta permite la creación de múltiples implementaciones de memoria (ej. Redis, PostgreSQL) sin afectar a los agentes que la utilizan. `InMemoryMemory` resuelve el problema de rendimiento al modificar directamente su lista interna, y al devolver una copia en `get_all()`, mantiene la inmutabilidad percibida por el consumidor. Esto prepara el framework para futuras estrategias de persistencia de memoria.
-   **Implicaciones**: Mayor eficiencia en la gestión de memoria para conversaciones largas. Facilita la extensión del framework con adaptadores de memoria persistente. Requiere que los agentes reciban una instancia de `BaseMemory` a través de DI.

### 4. Agent Registry v2

-   **Decisión**: El `AgentRegistry` en `agents/shared/registry.py` ha sido mejorado con la adición de los métodos `reset()`, `remove_agent()`, `get_agent()` y `list_agents()`. Los métodos `get()` y `list()` originales han sido renombrados a `get_agent()` y `list_agents()` respectivamente para mayor claridad y consistencia.
-   **Justificación**: La auditoría de la v1.1 señaló la falta de métodos para gestionar el registro de agentes de forma más dinámica, especialmente para entornos de testing paralelo. El método `reset()` es crucial para limpiar el estado del registro entre pruebas, evitando colisiones. `remove_agent()` permite la desvinculación explícita de agentes. Estos cambios mejoran la mantenibilidad y la testabilidad del registro, manteniendo el patrón de registro explícito y manual solicitado por el usuario.
-   **Implicaciones**: Mayor control sobre el ciclo de vida de los agentes registrados. Facilita el testing unitario y de integración. Los agentes que utilizaban `get()` y `list()` deberán actualizarse a los nuevos nombres de método.

### 5. Observabilidad Básica

-   **Decisión**: Se ha creado un nuevo subpaquete `agents/shared/observability/` con `events.py` y `metrics.py` (este último como placeholder). `events.py` implementa funciones para registrar eventos clave del ciclo de vida del agente (`agent_started`, `agent_finished`, `agent_failed`) utilizando el módulo de logging estándar de Python.
-   **Justificación**: La observabilidad es fundamental para entender el comportamiento de los sistemas multiagente en producción. La implementación de un sistema de eventos ligero permite capturar información crucial sobre la ejecución de los agentes sin introducir dependencias externas o complejidad. El uso del logging estándar de Python facilita la integración con sistemas de agregación de logs existentes. Los eventos se registran con metadatos contextuales (request_id, execution_id) para facilitar el seguimiento de trazas.
-   **Implicaciones**: Proporciona una base para el monitoreo y la depuración. Los agentes pueden invocar estas funciones de eventos en sus hooks de ciclo de vida. `metrics.py` queda como un placeholder para futuras integraciones con sistemas de métricas (ej. Prometheus, Grafana).

### 6. Mejoras en BaseAgent

-   **Decisión**: El método `run()` de `BaseAgent` ahora orquesta explícitamente la ejecución de los hooks de ciclo de vida (`before_run`, `execute`, `after_run`, `on_error`) y maneja los errores de forma uniforme, encapsulando cualquier excepción en un `AgentError`. El constructor de `BaseAgent` ha sido actualizado para aceptar las dependencias inyectadas (`llm_provider`, `memory`, `tools`).
-   **Justificación**: La orquestación explícita del ciclo de vida en `run()` garantiza que los hooks se ejecuten de manera consistente y que los errores sean capturados y manejados de forma centralizada. Esto mejora la robustez y reduce la duplicación de código en los agentes individuales. La inyección de dependencias en el constructor de `BaseAgent` es un paso crucial para el desacoplamiento y la testabilidad, permitiendo que los agentes utilicen las implementaciones de `BaseProvider`, `BaseMemory` y `BaseTool` proporcionadas por el contenedor de DI o directamente.
-   **Implicaciones**: Los agentes que hereden de `BaseAgent` ahora tienen un flujo de ejecución bien definido y un manejo de errores consistente. La inyección de dependencias facilita la configuración y el testing de los agentes.

## Consecuencias

-   **Positivas**:
    -   **Mayor Robustez**: El framework es más resistente a fallos de empaquetado y errores en tiempo de ejecución gracias a `importlib.resources` y el manejo unificado de excepciones.
    -   **Mejor Rendimiento**: La caché de prompts y la refactorización de `AgentMemory` optimizan el uso de recursos.
    -   **Escalabilidad Mejorada**: Las abstracciones `BaseProvider`, `BaseTool` y `BaseMemory` permiten una expansión significativa del ecosistema de agentes, herramientas y proveedores sin reescritura.
    -   **Testabilidad Superior**: La inyección de dependencias y los métodos `reset()` del registro facilitan la creación de tests unitarios y de integración aislados.
    -   **Observabilidad Básica**: Los eventos de logging proporcionan visibilidad sobre el comportamiento del agente.
    -   **Claridad Arquitectónica**: El ADR-010 documenta las decisiones clave, manteniendo la transparencia y la coherencia del diseño.

-   **Negativas**:
    -   **Curva de Aprendizaje**: La introducción de nuevas abstracciones y el patrón de DI pueden requerir un breve período de adaptación para los desarrolladores.
    -   **Refactorización de Agentes Existentes**: Los agentes `MatchAnalyst` y `Orchestrator` requerirán actualizaciones en sus constructores para aceptar las dependencias inyectadas y posiblemente en sus métodos `execute` si se desea aprovechar los nuevos hooks.

## Decisión Final

Las mejoras implementadas en la v1.2 del AI Agent Framework constituyen un "Enterprise Hardening" significativo. El framework está ahora excepcionalmente bien posicionado para integrar proveedores de LLM reales, un amplio conjunto de herramientas y estrategias de memoria persistente, manteniendo una arquitectura limpia, tipada y mantenible. Se ha logrado un equilibrio entre la funcionalidad avanzada y la simplicidad, evitando la sobreingeniería y la dependencia de frameworks externos complejos.
