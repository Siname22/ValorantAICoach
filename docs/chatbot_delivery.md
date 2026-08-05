# Práctica: Crear ChatBot con la app de escritorio de Google AI Studio

## Datos de la entrega

| Campo | Valor |
| --- | --- |
| **NOMBRE ALUMNO** | Raúl Poblete Illescas |
| **FECHA DE ENTREGA** | Pendiente |
| **ENLACE DE PÁGINA** | Pendiente del despliegue |
| **PLATAFORMA** | Streamlit Community Cloud + Google AI Studio (Gemini) |
| **GUÍA DE INSTALACIÓN** | [`docs/chatbot_installation.md`](chatbot_installation.md) |
| **PANTALLAZOS DEL CHATBOT** | Véase la sección [Pantallazos del chatbot](#pantallazos-del-chatbot) |
| **Chatbot** | Valorant AI Coach Assistant |
| **Repositorio** | https://github.com/Siname22/ValorantAICoach |

> **Antes de entregar:** complete el campo *FECHA DE ENTREGA*, sustituya
> *ENLACE DE PÁGINA* por la URL definitiva de la aplicación desplegada, con el
> formato `https://<nombre-app>.streamlit.app`, y añada las capturas indicadas en
> la sección de pantallazos. Ambos campos solo pueden completarse una vez
> finalizado el despliegue en Streamlit Community Cloud.

---

## Tecnologías utilizadas

| Tecnología | Función en el proyecto |
| --- | --- |
| **Python 3.12** | Lenguaje de implementación de todo el sistema |
| **Streamlit** | Interfaz web del chatbot y del resto de la aplicación |
| **Google AI Studio (Gemini)** | Modelo de lenguaje que genera las respuestas del coach |
| **FastAPI** | Backend REST que expone los datos de jugadores |
| **REST API** | Protocolo de comunicación entre el frontend y el backend |

El modelo empleado es **`gemini-2.5-flash`**, seleccionado por su equilibrio
entre latencia y calidad de razonamiento en conversaciones interactivas, y por
ser una generación consolidada con amplia disponibilidad. El modelo es
configurable mediante el secret opcional `GEMINI_MODEL`.

### Resiliencia frente a la saturación del modelo

Durante las pruebas de integración se comprobó que la API de Gemini puede
responder con un aviso temporal de alta demanda cuando el modelo solicitado está
saturado. Un fallo de esta naturaleza durante una demostración en directo sería
indistinguible de un defecto del sistema, de modo que el cliente no consulta un
único modelo: recorre una cadena ordenada.

| Orden | Modelo | Papel |
| --- | --- | --- |
| 1 | `GEMINI_MODEL`, o `gemini-2.5-flash` por defecto | Modelo primario |
| 2 | `gemini-2.5-flash-lite` | Variante ligera, habitualmente menos congestionada |
| 3 | `gemini-3.5-flash` | Generación más reciente, como último recurso |

Cada modelo se intenta hasta tres veces con una espera incremental de uno y dos
segundos. Si persiste la indisponibilidad, el cliente pasa al siguiente modelo de
forma transparente para el usuario. La distinción entre un fallo transitorio y
uno definitivo se realiza mediante el **código numérico de estado** que expone el
SDK, no por coincidencia de texto, lo que hace la clasificación independiente del
idioma y de la redacción de los mensajes del proveedor.

Este diseño incorpora un principio de comunicación deliberado: **ningún detalle
técnico llega al usuario**. Los códigos de estado, los identificadores de error
del proveedor y las trazas de excepción se registran en el log del servidor para
diagnóstico, mientras la interfaz muestra únicamente mensajes redactados en
español y orientados a la acción. El repertorio completo es reducido y
deliberadamente cerrado:

| Situación | Mensaje mostrado |
| --- | --- |
| Saturación, límite de cuota o timeout en toda la cadena | El servicio de IA está temporalmente saturado. Inténtalo de nuevo en unos segundos. |
| Credencial rechazada o modelo inaccesible | La configuración del servicio de IA necesita revisión. |
| Fallo no clasificado | El coach tuvo un problema inesperado. Inténtalo de nuevo. |
| Credencial ausente | Configura GEMINI_API_KEY para activar el coach. |

La interfaz añade además una última barrera: el bloque que invoca al coach captura
cualquier excepción no prevista, la registra en el log y muestra el mensaje
genérico. Su propósito no es corregir un fallo conocido, sino garantizar que un
defecto imprevisto no pueda desplegar una traza en una aplicación pública.

La integración se realiza con el SDK oficial **`google-genai`**. Conviene
señalar que el paquete `google-generativeai`, habitual en tutoriales anteriores,
fue **deprecado el 30 de noviembre de 2025** y su repositorio se renombró a
`deprecated-generative-ai-python`; por ese motivo se ha empleado el SDK vigente,
que es el recomendado en la documentación oficial de Google.

---

## Descripción del chatbot

El **Valorant AI Coach Assistant** se presenta como una funcionalidad real del
producto y no como un ejercicio aislado. Está integrado como una página más de
la aplicación, comparte la navegación lateral y reutiliza el mismo sistema de
diseño oscuro que el resto de la interfaz.

Su personalidad está definida mediante un *system prompt* profesional que lo
configura como analista competitivo y entrenador orientado al rango
**Plata–Platino**. El diseño de esta personalidad responde a un criterio
pedagógico concreto: el asistente prioriza decisiones que ganan rondas y evita
deliberadamente la teoría profesional de nivel VCT que un jugador de ese rango
no puede ejecutar, traduciendo cualquier concepto avanzado a una versión
aplicable.

Los dominios de análisis que cubre el asistente son once: agentes, roles, mapas,
economía, posicionamiento, tradeos, entry, comunicación, toma de decisiones,
errores de ronda y mejora individual. El asistente está orientado además al
escenario de **re-climb**, es decir, al jugador que intenta recuperar un rango
perdido.

Una decisión de diseño relevante es que el asistente **no inventa estadísticas**.
Mientras la integración con la Tracker API no esté conectada al chat, el
*system prompt* le indica explícitamente que no dispone de datos en vivo del
jugador, lo que evita que alucine rangos, K/D o historiales de partidas. Cuando
un dato concreto cambiaría su respuesta, el coach indica qué información
necesitaría consultar.

### Ejemplo de comportamiento

Ante la pregunta *"¿Qué agente debería jugar?"*, el asistente no responde con una
lista genérica de agentes. Razona sobre cuatro factores —el estilo de juego
declarado, las fortalezas y debilidades del jugador, el mapa concreto y el rol
que el equipo necesita— y sólo entonces recomienda uno o dos agentes explicando
la contrapartida de cada elección. Si falta alguno de esos cuatro datos, declara
la suposición que está asumiendo.

---

## Arquitectura de la solución

El flujo de la conversación sigue una separación de responsabilidades por capas:

```
Usuario
  ↓
Streamlit Chat            pages/6_AI_Coach.py
  ↓
Gemini Client             utils/gemini_client.py
  ↓
Valorant AI Knowledge     utils/coach_persona.py
  ↓
FastAPI / Tracker API     (preparado, no conectado)
```

Cada capa tiene una única responsabilidad. La página se limita a la
presentación; el cliente encapsula el transporte hacia Gemini, la traducción del
historial y el tratamiento de errores; y el módulo de personalidad contiene el
conocimiento del dominio sin ninguna dependencia de red, lo que permite revisarlo
y probarlo de forma independiente.

### Preparación para la integración futura

La cuarta capa está diseñada pero deliberadamente desactivada, conforme al
alcance acordado. La función `build_system_prompt()` acepta un parámetro opcional
`player_context`, y el cliente incluye las funciones `format_player_context()` y
`fetch_player_context()`. Cuando se decida conectar el chat con los endpoints de
FastAPI, bastará con completar el cuerpo de esa última función para que el coach
pase a dar consejos personalizados con estadísticas reales, sin modificar ni la
página ni la lógica del cliente.

### Gestión de credenciales

La clave de API se lee exclusivamente de `st.secrets`, con reserva a variables
de entorno, bajo el nombre `GEMINI_API_KEY`, y nunca aparece en el código fuente. El repositorio versiona
únicamente la plantilla `.streamlit/secrets.toml.example`, con valores de
ejemplo. El archivo real `.streamlit/secrets.toml` está excluido mediante
`.gitignore`.

---

## Guía de instalación

La guía detallada se encuentra en [`docs/chatbot_installation.md`](chatbot_installation.md).
A continuación se resume el procedimiento en cinco pasos.

**1. Crear el proyecto en Google AI Studio.** Acceder a
[aistudio.google.com](https://aistudio.google.com/) e iniciar sesión con una
cuenta de Google. No se requiere configurar facturación para el nivel gratuito.

**2. Obtener la API Key.** En [aistudio.google.com/apikey](https://aistudio.google.com/apikey),
seleccionar **Create API key** y copiar la credencial generada.

**3. Configurar los Streamlit Secrets.** En local, copiar la plantilla y
completar el valor:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```toml
GEMINI_API_KEY = "your_key_here"
GEMINI_MODEL = "gemini-2.5-flash"
```

En Streamlit Community Cloud, pegar el mismo contenido en **Settings → Secrets**.

**4. Ejecutar la aplicación.** Instalar las dependencias y arrancar el servidor:

```bash
pip install -r frontend/streamlit_app/requirements.txt
streamlit run frontend/streamlit_app/app.py
```

La aplicación queda disponible en `http://localhost:8501`; la página del
asistente se abre desde la entrada **AI Coach** de la navegación lateral.

**5. Acceder al chatbot y desplegar.** Publicar los cambios en la rama
conectada a Streamlit Community Cloud, añadir el secret `GEMINI_API_KEY` en el
panel de la aplicación y esperar a que finalice la reconstrucción automática.
Si el secret no está configurado, la página no falla: muestra el aviso
*"Configura GEMINI_API_KEY para activar el coach."* y el resto de la aplicación
sigue operando con normalidad.

| Parámetro de despliegue | Valor |
| --- | --- |
| Main file path | `frontend/streamlit_app/app.py` |
| Versión de Python | `3.12` |
| Archivo de dependencias | `frontend/streamlit_app/requirements.txt` |

---

## Pantallazos del chatbot

_Insertar en esta sección las capturas de pantalla de la aplicación desplegada._

### 1. Página principal de la aplicación

_Captura de la página Home mostrando la navegación lateral con la entrada
**AI Coach** visible._

<!-- ![Home](img/01_home.png) -->

### 2. Página del chatbot antes de la conversación

_Captura de la página **AI Coach** con el mensaje de bienvenida y las cuatro
preguntas sugeridas._

<!-- ![AI Coach inicial](img/02_ai_coach_inicial.png) -->

### 3. Conversación con el asistente

_Captura de un intercambio completo: una pregunta sobre selección de agente y la
respuesta razonada del coach._

<!-- ![Conversación](img/03_conversacion.png) -->

### 4. Configuración de la API Key en Google AI Studio

_Captura de la pantalla de creación de la clave en Google AI Studio, **ocultando
la credencial completa**._

<!-- ![Google AI Studio](img/04_google_ai_studio.png) -->

### 5. Secrets configurados en Streamlit Community Cloud

_Captura del panel **Settings → Secrets**, **ocultando el valor de la clave**._

<!-- ![Secrets](img/05_secrets.png) -->

### 6. Aplicación desplegada en Streamlit Community Cloud

_Captura del navegador con la URL pública visible y el chatbot en
funcionamiento._

<!-- ![Despliegue](img/06_despliegue.png) -->

> **Recomendación:** guardar las imágenes en `docs/img/` y descomentar la línea
> Markdown correspondiente para incrustarlas. Verifique que ninguna captura
> muestre la clave de API completa.

---

## Verificación realizada

Antes de la entrega se ejecutaron pruebas locales sobre el entorno del proyecto
(Python 3.12, Streamlit) con los siguientes resultados:

| Comprobación | Resultado |
| --- | --- |
| Resolución del archivo de dependencias | `frontend/streamlit_app/requirements.txt` |
| Importación del SDK `google.genai` | Correcta |
| Importación del entrypoint y de las 6 páginas | Correcta |
| Arranque del servidor Streamlit | Sin errores |
| Respuesta de las rutas, incluida `/6_AI_Coach` | HTTP 200 |
| Suite funcional del cliente y la personalidad | 88 de 88 comprobaciones superadas |
| Suite de resiliencia (`tests/test_gemini_resilience.py`) | 81 de 81 comprobaciones superadas |
| Carga de la página sin `GEMINI_API_KEY` configurada | Aviso mostrado, aplicación operativa |

La suite funcional validó la resolución de la credencial `GEMINI_API_KEY` y de su
nombre heredado, la construcción del *system prompt* con los once dominios, la
conversión del historial al formato del SDK, la traducción del rol `assistant` a
`model`, el descarte de turnos vacíos, el respeto del límite de historial, la
ausencia de importaciones del SDK deprecado y seis escenarios de error: clave
inválida, cuota agotada, modelo no disponible, error de servidor, respuesta vacía
y fallo inesperado de red. Las pruebas emplean un doble de la API, por lo que no
consumen cuota ni requieren una clave real.

La comprobación del comportamiento sin credencial se realizó retirando
temporalmente el archivo de secrets y las variables de entorno: la página
**AI Coach** cargó correctamente con el aviso *"Configura GEMINI_API_KEY para
activar el coach."*, y el registro del servidor no presentó excepciones.

La suite de resiliencia verificó de forma específica el comportamiento ante la
saturación del modelo. Se confirmó que un aviso de alta demanda en el modelo
primario desencadena tres reintentos con espera incremental, que a continuación
se recurre automáticamente al modelo de respaldo y que **el usuario recibe una
respuesta válida**. También se comprobó el caso opuesto: cuando la cadena
completa está indisponible, el mensaje mostrado no contiene el código de estado,
ni el identificador de error del proveedor, ni traza alguna. Un fallo transitorio
que se resuelve en el segundo intento no llega a cambiar de modelo, y una
credencial rechazada no se reintenta en absoluto, evitando consumo innecesario de
cuota.

Esta suite quedó incorporada al repositorio como
`frontend/streamlit_app/tests/test_gemini_resilience.py`, de modo que la
verificación es reproducible por cualquier evaluador sin necesidad de credencial.
El informe `docs/gemini_resilience_report.md` detalla la estrategia, los cinco
escenarios cubiertos y los resultados registrados.

---

## Archivos entregados

| Archivo | Descripción |
| --- | --- |
| `frontend/streamlit_app/pages/6_AI_Coach.py` | Página del chatbot |
| `frontend/streamlit_app/utils/gemini_client.py` | Cliente de Google AI Studio |
| `frontend/streamlit_app/utils/coach_persona.py` | Personalidad y conocimiento del coach |
| `frontend/streamlit_app/components/sections.py` | Renderizado de la interfaz de chat |
| `frontend/streamlit_app/utils/ui.py` | Estilos del chat y enlace de navegación |
| `frontend/streamlit_app/requirements.txt` | Dependencia `google-genai` |
| `frontend/streamlit_app/tests/test_gemini_resilience.py` | Suite de resiliencia sin consumo de cuota |
| `docs/gemini_resilience_report.md` | Informe de resiliencia y resultados |
| `.streamlit/secrets.toml.example` | Plantilla de configuración |
| `docs/chatbot_installation.md` | Guía de instalación |
| `docs/chatbot_delivery.md` | Este documento |
