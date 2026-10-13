# ADR-014: Selección de Streamlit como Frontend Interactivo frente a Alternativas SPA

## Estado
Aceptado

## Contexto
El proyecto Valorant AI Coach requería una interfaz de usuario interactiva y profesional para presentar el análisis táctico, visualizaciones de mapas y trayectorias, análisis de repeticiones y chat en tiempo real con el AI Coach de Gemini. Se evaluaron las siguientes alternativas principales:
1. **Single Page Application (SPA) con React / Next.js / TypeScript**.
2. **Framework Web SSR en Python (Django / Jinja2 / HTMX)**.
3. **Streamlit (Python Data / Dashboard Framework)**.

## Decisión
Se decidió adoptar **Streamlit** como la capa de frontend para el producto y las demostraciones interactivas, bajo una estricta regla de aislamiento arquitectónico:
- El frontend reside en su propio directorio (`frontend/`) y se empaqueta en una imagen de Docker separada.
- No importa módulos internos del backend (`backend.*`) ni accede a la base de datos de persistencia.
- Se comunica exclusivamente mediante HTTP REST a través de `APIClient`.

## Justificación

1. **Velocidad de Iteración y Enfoque en Inteligencia Artificial**:
   Streamlit permite construir interfaces ricas con soporte nativo para chat (`st.chat_message`, `st.chat_input`), componentes interactivos de datos y gráficos Plotly sin la sobrecarga de mantener un pipeline complejo de Node.js, Webpack/Vite y sincronización de tipos manual entre TypeScript y Python.

2. **Alineación con el Ecosistema de Ciencia de Datos y Visualización**:
   Las bibliotecas de análisis visual y gráficos de radar/trayectoria (Plotly, Pandas) se integran directamente con Streamlit sin conversiones complejas de serialización en el cliente.

3. **Demostraciones en Vivo y Streamlit Community Cloud**:
   Permite desplegar fácilmente entornos de demo interactivos para evaluadores, reclutadores y usuarios finales manteniendo un único lenguaje en el repositorio (Python 3.12+).

4. **Garantía de Aislamiento HTTP**:
   Al obligar a que Streamlit consuma el backend mediante `APIClient` sobre HTTP REST, se garantiza que el backend sea verdaderamente headless y que cualquier futura migración a un frontend móvil o web (e.g., React/Flutter) sea trivial, ya que todos los contratos REST y DTOs ya están establecidos y probados.

## Consecuencias
- **Positivas**:
  - Desarrollo ágil de UI reactiva con gráficos y chat conversacional integrados.
  - Eliminación de dependencias de Node.js en el entorno de desarrollo principal.
  - Desacoplamiento arquitectónico verificado por tests unitarios independientes (`frontend/streamlit_app/tests`).
- **Negativas**:
  - Streamlit re-ejecuta el script de la página ante cambios de estado; se requiere gestión cuidadosa de `st.session_state` y cacheo de clientes.
  - Menor control sobre CSS y micro-animaciones en comparación con una SPA nativa en Tailwind CSS/React.
