\# ADR-012: Riot Provider SDK Integration



\## Estado



Propuesto



\## Contexto



ValorantAICoach necesita integrar datos oficiales de Riot Games

para obtener información fiable de jugadores, partidas y estadísticas.



Actualmente existen providers separados:

\- Tracker Provider

\- LLM Provider

\- Screenshot Provider



La integración Riot debe mantener la arquitectura desacoplada.



\## Decisión



Crear un Riot Provider siguiendo la interfaz común del Provider SDK.



Responsabilidades:



\- Obtener información de cuenta Riot

\- Obtener historial de partidas

\- Obtener detalles de partidas

\- Normalizar modelos para los agentes IA



\## Arquitectura



Usuario

&#x20;|

OrchestratorAgent

&#x20;|

MatchAnalystAgent

&#x20;|

RiotProvider



\## Consecuencias



Positivas:

\- Fuente oficial de datos

\- Menor dependencia de terceros

\- Mejor calidad del análisis



Negativas:

\- Gestión de rate limits

\- Necesidad de API Key

\- Dependencia externa

