# T03: validación real

Esta guía se ejecuta desde `D:\Programas\Repos_GitHub\ValorantAICoach-t03` en una máquina con Docker Compose, Chrome, acceso autorizado a un proveedor de datos y dos Riot IDs de prueba con regiones conocidas. No sustituye la comprobación de permisos y consentimiento de T02. No incluyas claves, contraseñas ni tokens en capturas, logs o informes.

## Preparación

1. Si `.env.t03` no existe, copia `.env.example` a `.env.t03`. Si ya existe, edita **esa copia local sin sobrescribirla**. Git ignora `.env.t03`. Tras instalar Docker Desktop, abre una terminal nueva para que `docker` esté en `PATH`.
2. Configura `APP_ENV=staging`, `DATABASE_ENABLED=true`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` (con el mismo usuario, contraseña y base de datos, usando `postgres` como host), `JWT_SECRET_KEY` (32 caracteres o más) y al menos una clave de proveedor autorizada (`RIOT_API_KEY`, `HENRIK_API_KEY` o `TRACKER_API_KEY`). Desactiva los proveedores sin clave con su variable `*_ENABLED=false`. Si la contraseña contiene caracteres reservados de URL, codifícalos en `DATABASE_URL`.
3. Elige dos Riot IDs reales de prueba, A y B, y anota sus regiones correctas fuera del repositorio. Necesitarás una cuenta de la aplicación para generar informes.

```powershell
if (-not (Test-Path .env.t03)) { Copy-Item .env.example .env.t03 }
notepad .env.t03
docker compose --env-file .env.t03 config --quiet
docker compose --env-file .env.t03 build backend frontend
docker compose --env-file .env.t03 up -d postgres
docker compose --env-file .env.t03 ps postgres
docker compose --env-file .env.t03 run --rm backend uv run --no-sync alembic upgrade head
docker compose --env-file .env.t03 up -d backend frontend
```

`ps postgres` debe mostrar `healthy` antes de migrar. Comprueba `/health/live`, `/health/ready` y `/health` en `http://127.0.0.1:8000`; `/health` debe confirmar que el proveedor elegido responde. Abre `http://127.0.0.1:8080` en Chrome.

## Recorrido que debe registrarse

1. Registra o inicia sesión. En **Resumen**, busca A con su región. Confirma que el perfil y las partidas proceden del proveedor real; anota IDs de partida y la región de las peticiones de red, sin copiar datos personales al informe.
2. Abre **Partidas** y comprueba que aparecen las partidas de A. Inspecciona una línea temporal disponible; si el proveedor no entrega rondas, debe aparecer un estado de ausencia o error, nunca rondas de muestra.
3. Abre **Informes**, genera uno para A y comprueba que el historial lo recupera. En la red del navegador, verifica que `POST /players/A/TAG/reports`, `GET /players/A/TAG/reports` y `GET /players/A/TAG/progression` usan la región elegida. La respuesta nueva debe incluir `payload.region` con esa región.
4. Vuelve a **Resumen**, cambia a B y su región y visita **Partidas** e **Informes**. No deben quedar perfil, partidas ni informes de A. Repite con el mismo Riot ID en otra región si hay datos autorizados para ambas; el historial regional no debe mezclar informes.
5. Activa la limitación de red de Chrome, inicia una búsqueda de A y cambia a B antes de que responda A. La respuesta tardía de A no debe sustituir a B. Bloquea temporalmente una petición de partidas o informes desde DevTools y verifica que el error no muestra datos ficticios; desactiva el bloqueo después.
6. Recarga la página y vuelve a **Resumen**: deben restaurarse Riot ID y región. Reinicia solo `backend` y `frontend` con `docker compose --env-file .env.t03 restart backend frontend`; comprueba que el informe generado sigue en el historial correcto.

Registra fecha, commit, versiones, proveedor utilizado (sin clave), regiones, resultados de cada paso y cualquier error. T03 solo se acepta si el recorrido completo pasa con proveedor y PostgreSQL reales.

## Informes anteriores

Los informes guardados antes de T03 no tienen región ni propietario verificable. Permanecen en la base de datos, pero las consultas API autenticadas filtran por el usuario que generó cada informe: los registros antiguos sin propietario no aparecen ni se recuperan por ID. No se atribuyen automáticamente a una región o usuario porque esos datos no se pueden deducir de forma fiable. La migración `20261126_01` añade el propietario nullable y conserva los registros anteriores.

Las lecturas de historial, progresión y detalle requieren sesión. Los informes nuevos solo son visibles para el usuario que los generó y, cuando se solicita una región, para esa región. La vinculación de una cuenta de jugador sigue siendo una declaración del usuario; verificar que es su titular exige el proceso de permisos previsto en T02/T06.

Para una región seleccionada, HenrikDev verifica la región real de la cuenta antes de utilizar datos de HenrikDev, Tracker o Riot. Si no hay un verificador regional disponible, la API devuelve un error explícito en vez de asignar la región configurada de Riot a la cuenta. Las instantáneas regionales anteriores quedan fuera de la nueva versión de claves de caché y expiran por su TTL normal.

Al terminar, `docker compose --env-file .env.t03 down` detiene los contenedores y conserva el volumen PostgreSQL. No uses `down -v` si necesitas conservar los datos de la prueba.

## Estado local y separación del commit ajeno

El 26 de noviembre de 2026 se instaló Docker Desktop por usuario y se verificaron Docker Engine 29.9.3 y Compose v5.7.1. `.env.t03` existe con configuración y secretos locales, está ignorado por Git y **no debe sobrescribirse**. La clave del proveedor no se copia a esta guía ni a los resultados.

### Resultado de la prueba de aceptación

- Las imágenes `backend` y `frontend` compilaron. PostgreSQL 16 estuvo sano, Alembic llegó a `20261013_01 (head)`, `/health/ready` devolvió `database=connected` y `providers_configured=1`, y HenrikDev respondió en `/health`.
- Dos cuentas de prueba autorizadas de la región EU devolvieron perfiles y partidas distintos desde HenrikDev. Resumen y Partidas mostraron los datos correspondientes al jugador activo, sin filas de muestra. La vista de rondas no estuvo disponible (503) y mostró un error explícito sin datos de ejemplo.
- Informes exigió inicio de sesión. Se corrigió el formulario, que enviaba un nombre de usuario donde la API exige email. Una cuenta local de prueba pudo entrar y generar un informe nuevo para el jugador A en EU. El historial regional recuperó un informe; `payload.region=eu` se confirmó tanto en la API como en PostgreSQL. La consulta de NA devolvió cero informes.
- El proveedor devolvía las mismas partidas al consultar la cuenta europea con región NA. Se corrigió la aplicación para validar la región real de la cuenta antes de mostrar perfil o partidas. Después de invalidar solo las instantáneas de prueba anteriores, las consultas de perfil y partidas en NA devolvieron 404 y las de EU devolvieron 200. La interfaz vació las tarjetas al elegir NA y restauró el informe al regresar a EU.
- Al cambiar de A a B, el informe de A desapareció de Informes y las partidas de B sustituyeron las de A. Tras recargar Resumen se conservaron el Riot ID y la región. Tras reiniciar backend y frontend, el informe EU seguía accesible en la interfaz y en la API.
- En Chrome automatizado se retrasó la respuesta de A hasta después de cargar B: B permaneció visible. Al cortar una petición de partidas, apareció el error explícito y solo la fila de estado vacío, sin datos ficticios.
- Compilación y lint del frontend, 66 pruebas del frontend y 491 pruebas del backend pasaron. También pasaron Ruff, Black y `git diff --check`.

**Resultado:** los criterios funcionales de T03 se verificaron con HenrikDev y PostgreSQL reales. Esta aceptación no certifica otros proveedores ni el detalle por rondas cuando el proveedor no lo entrega. En esta base de prueba no había informes anteriores sin región; su tratamiento se verificó en código y pruebas, no con un registro histórico real.

La prueba real anterior corresponde al código previo a la revisión de la PR #13. Tras añadir la migración de propiedad y los controles de lectura, se deben repetir el registro/inicio de sesión, la generación y la recuperación de un informe con el proveedor y PostgreSQL reales antes de aceptar funcionalmente el nuevo commit. La CI verifica la migración y la persistencia en PostgreSQL con datos sintéticos.

El commit `ca32238` modifica solo archivos de `lol-mod/map-dimensional/` y está en la base de `feature/t03-player-identity`. Se conserva expresamente en la rama local `codex/preserve-lol-map-audit-ca32238`. No muevas ni restablezcas la rama T03 mientras tenga cambios sin confirmar. Cuando termine la validación real, confirma **solo** los archivos de T03 y prepara una rama de integración nueva desde `d353aea` mediante `git cherry-pick` del commit T03. Comprueba que el diff de la rama nueva no contenga `lol-mod/` y repite las pruebas. Mantén la rama y el worktree actuales hasta verificar esa copia; así el commit de mapas y todos los cambios de T03 conservan sus referencias originales.
