# ADR-009: AI Agent Framework v1.1 Evolution

## Estado

Aceptado

## Contexto

El AI Agent Framework v1.0 fue implementado como una base sólida para el proyecto ValorantAICoach, siguiendo principios de Clean Architecture, DDD y SOLID. Una auditoría técnica crítica posterior identificó áreas clave de mejora en robustez, escalabilidad y mantenibilidad, especialmente en la carga de prompts, la abstracción de herramientas y la gestión del ciclo de vida de los agentes. El objetivo de esta evolución a v1.1 es abordar estas deficiencias sin introducir complejidad innecesaria o dependencias externas prematuras.

## Decisiones

### 1. PromptLoader: Migración a `importlib.resources` y Caché

- **Decisión**: El `PromptLoader` ha sido refactorizado para utilizar `importlib.resources` en lugar de `pathlib.Path` para la carga de archivos `prompt.md`. Además, se ha integrado `functools.lru_cache` para almacenar en caché los prompts cargados.
- **Justificación**: La dependencia de `pathlib.Path` y `__file__` para localizar prompts es frágil en entornos de producción donde el código puede ser empaquetado (e.g., `.whl`, PyInstaller) o ejecutado desde un ZIP. `importlib.resources` es el método estándar y robusto de Python para acceder a recursos dentro de paquetes, garantizando la compatibilidad con el empaquetado. La adición de `lru_cache` mitiga el cuello de botella de rendimiento identificado en la auditoría, donde la lectura de disco ocurría en cada inicialización de agente, mejorando la eficiencia para cientos de prompts.
- **Implicaciones**: Mayor robustez en despliegues. Mejora de rendimiento. No rompe la API existente de `PromptLoader.load_prompt`.

### 2. BaseTool: Abstracción para Herramientas

- **Decisión**: Se ha introducido una nueva clase abstracta `BaseTool` y un `ToolSchema` (basado en Pydantic) en `agents/shared/base_tool.py`. `BaseTool` define una interfaz común para todas las herramientas, incluyendo `name`, `description`, `schema` (para validación de entrada y compatibilidad con Function Calling de LLMs) y un método `execute` asíncrono. Los métodos `available_tools()` en `match_analyst/tools.py` y `orchestrator/tools.py` han sido actualizados para devolver instancias de `BaseTool`.
- **Justificación**: La auditoría destacó que el `list[str]` actual para herramientas era insuficiente para escalar a 50+ herramientas y para la integración con LLMs. `BaseTool` proporciona una abstracción formal que permite:
    - **Tipado Fuerte**: Definir claramente las entradas y salidas de las herramientas.
    - **Validación de Esquemas**: Utilizar Pydantic para validar los argumentos de las herramientas, esencial para la seguridad y la robustez.
    - **Compatibilidad con LLMs**: El `schema` Pydantic puede ser fácilmente convertido a JSON Schema, el formato estándar para Function Calling en la mayoría de los LLMs (OpenAI, Gemini, etc.).
    - **Extensibilidad**: Facilita la adición de nuevas herramientas (Tracker, Henrik, etc.) de manera estandarizada.
- **Implicaciones**: Preparación para la integración con LLMs y un ecosistema de herramientas complejo. Mayor claridad y seguridad en la invocación de herramientas. Requiere que las implementaciones de herramientas hereden de `BaseTool`.

### 3. Hooks del Ciclo de Vida en BaseAgent

- **Decisión**: Se han añadido tres métodos asíncronos opcionales a `BaseAgent`: `before_run`, `after_run` y `on_error`. Estos métodos tienen implementaciones por defecto vacías (`pass`).
- **Justificación**: La auditoría identificó la falta de *hooks* como una limitación para la extensibilidad y la implementación de lógica transversal (logging, telemetría, manejo de errores centralizado). Al hacerlos opcionales, se mantiene la compatibilidad con los agentes existentes y se permite a los desarrolladores implementar solo los hooks necesarios, siguiendo el principio de 
responsabilidad única y el principio Open/Closed.
- **Implicaciones**: Mayor flexibilidad para añadir lógica de pre-procesamiento, post-procesamiento y manejo de errores a nivel de agente sin modificar la lógica central de `run()`. No impacta a los agentes existentes que no los implementen.

### 4. No Implementación de `@register_agent`

- **Decisión**: Se ha pospuesto la implementación de un decorador `@register_agent`.
- **Justificación**: Aunque la auditoría lo sugirió como una mejora de limpieza, la solicitud del usuario prioriza evitar la 
introducción de "magia" prematuramente y mantener el registro explícito y manual. Esto asegura que el flujo de registro sea siempre visible y controlable, lo cual es beneficioso para la depuración y la comprensión del sistema en sus etapas iniciales.
- **Implicaciones**: El registro manual sigue siendo necesario en cada archivo `agent.py`. No hay impacto negativo en la funcionalidad actual.

## Consecuencias

- **Positivas**:
    - El framework es ahora más robusto frente a los despliegues y el empaquetado gracias a `importlib.resources`.
    - El rendimiento de carga de prompts mejora significativamente con el caché.
    - La abstracción `BaseTool` prepara el terreno para una integración sofisticada con LLMs y un ecosistema de herramientas escalable.
    - Los *hooks* de ciclo de vida ofrecen puntos de extensión clave sin afectar la lógica central de los agentes.
    - La documentación ADR proporciona un registro claro de las decisiones arquitectónicas.

- **Negativas**:
    - El registro manual de agentes sigue siendo una fuente potencial de errores humanos.
    - La inmutabilidad de `AgentMemory` sigue siendo un problema de rendimiento para conversaciones muy largas, aunque no es una prioridad para esta fase.

## Decisión Final

Las mejoras implementadas en la v1.1 del AI Agent Framework abordan los puntos críticos de la auditoría, mejorando la robustez, el rendimiento y la extensibilidad de manera controlada y sin introducir complejidad innecesaria. El framework está ahora mejor posicionado para futuras integraciones con LLMs y un crecimiento significativo en el número de agentes y herramientas.
Inversión de Dependencias (DIP) y el principio Open/Closed.
- **Implicaciones**: Mayor flexibilidad para añadir lógica de pre-procesamiento, post-procesamiento y manejo de errores a nivel de agente sin modificar la lógica central de `run()`. No impacta a los agentes existentes que no los implementen.

### 4. No Implementación de `@register_agent`

- **Decisión**: Se ha pospuesto la implementación de un decorador `@register_agent`.
- **Justificación**: Aunque la auditoría lo sugirió como una mejora de limpieza, la solicitud del usuario prioriza evitar la introducción de "magia" prematuramente y mantener el registro explícito y manual. Esto asegura que el flujo de registro sea siempre visible y controlable, lo cual es beneficioso para la depuración y la comprensión del sistema en sus etapas iniciales.
- **Implicaciones**: El registro manual sigue siendo necesario en cada archivo `agent.py`. No hay impacto negativo en la funcionalidad actual.

## Consecuencias

- **Positivas**:
    - El framework es ahora más robusto frente a los despliegues y el empaquetado gracias a `importlib.resources`.
    - El rendimiento de carga de prompts mejora significativamente con el caché.
    - La abstracción `BaseTool` prepara el terreno para una integración sofisticada con LLMs y un ecosistema de herramientas escalable.
    - Los *hooks* de ciclo de vida ofrecen puntos de extensión clave sin afectar la lógica central de los agentes.
    - La documentación ADR proporciona un registro claro de las decisiones arquitectónicas.

- **Negativas**:
    - El registro manual de agentes sigue siendo una fuente potencial de errores humanos.
    - La inmutabilidad de `AgentMemory` sigue siendo un problema de rendimiento para conversaciones muy largas, aunque no es una prioridad para esta fase.

## Decisión Final

Las mejoras implementadas en la v1.1 del AI Agent Framework abordan los puntos críticos de la auditoría, mejorando la robustez, el rendimiento y la extensibilidad de manera controlada y sin introducir complejidad innecesaria. El framework está ahora mejor posicionado para futuras integraciones con LLMs y un crecimiento significativo en el número de agentes y herramientas.
Responsabilidad Única y el Principio Open/Closed.
- **Implicaciones**: Mayor flexibilidad para añadir lógica de pre-procesamiento, post-procesamiento y manejo de errores a nivel de agente sin modificar la lógica central de `run()`. No impacta a los agentes existentes que no los implementen.

### 4. No Implementación de `@register_agent`

- **Decisión**: Se ha pospuesto la implementación de un decorador `@register_agent`.
- **Justificación**: Aunque la auditoría lo sugirió como una mejora de limpieza, la solicitud del usuario prioriza evitar la introducción de "magia" prematuramente y mantener el registro explícito y manual. Esto asegura que el flujo de registro sea siempre visible y controlable, lo cual es beneficioso para la depuración y la comprensión del sistema en sus etapas iniciales.
- **Implicaciones**: El registro manual sigue siendo necesario en cada archivo `agent.py`. No hay impacto negativo en la funcionalidad actual.

## Consecuencias

- **Positivas**:
    - El framework es ahora más robusto frente a los despliegues y el empaquetado gracias a `importlib.resources`.
    - El rendimiento de carga de prompts mejora significativamente con el caché.
    - La abstracción `BaseTool` prepara el terreno para una integración sofisticada con LLMs y un ecosistema de herramientas escalable.
    - Los *hooks* de ciclo de vida ofrecen puntos de extensión clave sin afectar la lógica central de los agentes.
    - La documentación ADR proporciona un registro claro de las decisiones arquitectónicas.

- **Negativas**:
    - El registro manual de agentes sigue siendo una fuente potencial de errores humanos.
    - La inmutabilidad de `AgentMemory` sigue siendo un problema de rendimiento para conversaciones muy largas, aunque no es una prioridad para esta fase.

## Decisión Final

Las mejoras implementadas en la v1.1 del AI Agent Framework abordan los puntos críticos de la auditoría, mejorando la robustez, el rendimiento y la extensibilidad de manera controlada y sin introducir complejidad innecesaria. El framework está ahora mejor posicionado para futuras integraciones con LLMs y un crecimiento significativo en el número de agentes y herramientas.
