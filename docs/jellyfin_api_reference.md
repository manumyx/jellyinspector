# Jellyfin API - Referencia Rápida

> Documentación empírica obtenida durante el desarrollo de JellyInspector.
> Complementa la [documentación oficial](https://api.jellyfin.org/).

## Autenticación

Todas las peticiones llevan el header:
```
X-Emby-Token: <API_KEY>
```

## Endpoints Clave

### Items

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/Users/{userId}/Items/{itemId}` | Obtener el `BaseItemDto` completo de un ítem |
| `GET` | `/Items?includeItemTypes=Series&recursive=true` | Buscar ítems en toda la biblioteca |
| `POST` | `/Items/{itemId}` | **Actualizar** metadatos (envía el `BaseItemDto` completo) |

### Series / Temporadas / Episodios

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/Shows/{seriesId}/Seasons?userId={userId}` | Listar temporadas |
| `GET` | `/Shows/{seriesId}/Episodes?userId={userId}&fields=Overview,Path` | Listar episodios |

### Biblioteca

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/Library/Refresh` | Forzar escaneo completo de la biblioteca |

### Imágenes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/Items/{itemId}/RemoteImages/Download?type=Primary&imageUrl={url}` | Descargar imagen remota y asignarla |

## Bugs Conocidos y Quirks

### 1. `POST /Items/{itemId}` requiere el objeto COMPLETO
No es un PATCH. Debes hacer `GET` primero, modificar los campos, y enviar todo el objeto de vuelta.

### 2. `OriginalTitle` nunca puede ser `null`
Si envías `"OriginalTitle": null`, Jellyfin devuelve `400 Bad Request`. Siempre usar `""` (string vacío).

### 3. `LockedFields` solo acepta ciertos valores
Valores seguros:
- `"Name"` ✅
- `"Overview"` ✅

Valores que causan `400 Bad Request`:
- `"OriginalTitle"` ❌
- `"IndexNumber"` ❌
- `"ParentIndexNumber"` ❌

### 4. Temporadas Fantasma (Ghost Seasons)
Cuando la opción **"Mostrar elementos faltantes"** está activa, Jellyfin crea temporadas virtuales desde TMDB con `IndexNumber: 1, 2, 3...`. Si tus carpetas físicas tienen nombres no estándar (ej. `[Anime Time] Re Zero Season 02`), Jellyfin no las conecta y crea un segundo grupo con `IndexNumber: null`.

**Solución:** Inyectar el `IndexNumber` correcto vía API en la temporada huérfana y ejecutar un Refresco de Biblioteca. Las temporadas se fusionarán automáticamente.

### 5. El scraper de fondo puede revertir cambios
Después de un `POST /Library/Refresh`, los plugins de metadata (TMDB, AniDB) se ejecutan en segundo plano. Si no has bloqueado los campos con `LockedFields`, los scrapers sobrescribirán tus cambios con datos (posiblemente incorrectos) de sus fuentes.

**Solución:** Siempre añadir `"Name"` y `"Overview"` al array `LockedFields` antes de hacer el POST.
