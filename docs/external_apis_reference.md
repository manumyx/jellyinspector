# APIs Externas - Referencia Rápida

> Documentación de las APIs de terceros usadas por JellyInspector.

---

## Jikan v4 (MyAnimeList no-oficial)

**Base URL:** `https://api.jikan.moe/v4`

**Rate Limit:** 3 peticiones/segundo, 60/minuto. Devuelve `429 Too Many Requests` si se excede.

### Endpoints usados

| Endpoint | Descripción |
|----------|-------------|
| `GET /anime/{mal_id}` | Datos completos de un anime (para películas: título, sinopsis) |
| `GET /anime/{mal_id}/episodes/{ep_num}` | Título y sinopsis de un episodio específico |

### Campos útiles de la respuesta

**Anime completo (`/anime/{id}`):**
```json
{
  "data": {
    "title": "Kizumonogatari I: Tekketsu-hen",
    "title_english": "Kizumonogatari Part 1: Iron-Blooded",
    "synopsis": "During Koyomi Araragi's second year..."
  }
}
```

**Episodio (`/anime/{id}/episodes/{ep}`):**
```json
{
  "data": {
    "title": "Hitagi Crab, Part One",
    "synopsis": "Koyomi catches his classmate Hitagi..."
  }
}
```

### Manejo de errores
- `429`: Esperar con backoff exponencial (2s, 4s, 8s).
- `504 Gateway Timeout`: Reintentar hasta 2 veces.
- Respuesta vacía: Marcar como "fallido" y continuar. El script es incremental, así que se puede relanzar.

---

## AniList GraphQL

**Endpoint:** `https://graphql.anilist.co` (POST)

**Rate Limit:** 90 peticiones/minuto. Generoso.

### Query para buscar anime o novela

```graphql
query ($search: String) {
  Page(page: 1, perPage: 1) {
    media(search: $search, type: ANIME) {
      title { romaji english }
      coverImage { extraLarge }
    }
  }
}
```

Para novelas ligeras (mejores portadas para series con muchos arcos):
```graphql
media(search: $search, type: MANGA, format: NOVEL)
```

### ¿Cuándo usar NOVEL vs ANIME?
- **NOVEL**: Para series como Monogatari donde cada arco tiene su propia portada de novela (Bakemonogatari, Nisemonogatari, etc.). TMDB agrupa todo en una sola serie.
- **ANIME**: Para series estándar donde la portada del anime es suficiente.

---

## TMDB API v3

**Base URL:** `https://api.themoviedb.org/3`

**Autenticación:** Bearer token en el header `Authorization`.

### Endpoints útiles

| Endpoint | Descripción |
|----------|-------------|
| `GET /search/tv?query=...` | Buscar series |
| `GET /tv/{id}/episode_groups` | Grupos de episodios alternativos |
| `GET /tv/episode_group/{group_id}` | Detalle de un grupo |
| `GET /tv/{id}/season/{s}/episode/{e}` | Detalle de un episodio |

### Imágenes
Base URL para imágenes: `https://image.tmdb.org/t/p/original{path}`
